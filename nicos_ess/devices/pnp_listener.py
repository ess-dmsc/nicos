# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2024 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************
import re
import socket
import threading
import time

from nicos import session
from nicos.core import SIMULATION, MAIN, POLLER
from nicos.devices.epics.pva.p4p import pvget, pvput
from nicos.utils import createThread
from nicos.core.device import Device, Param


class UDPHeartbeatsManager(Device):
    parameters = {
        "port": Param("UDP port to listen on", type=int, mandatory=True),
    }

    _pv_list = []
    _heartbeat_thread = None
    _listener_thread = None
    _lock = threading.Lock()

    def doPreinit(self, mode):
        if session.sessiontype != POLLER and mode != SIMULATION:
            self._create_socket()
            self._bind_socket()
            self._stop_event = threading.Event()

    def doInit(self, mode):
        if session.sessiontype != POLLER and mode != SIMULATION:
            self._listener_thread = createThread("udp_thread", self._listen_for_packets)
            self._heartbeat_thread = createThread(
                "heartbeat_thread", self._send_heartbeats
            )

    def _create_socket(self):
        if session.sessiontype == MAIN:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.settimeout(1)

    def _bind_socket(self):
        if session.sessiontype == MAIN:
            for i in range(1, 11):
                retry_time = i
                try:
                    self._sock.bind(("", self.port))
                    return
                except OSError as e:
                    self.log.debug(
                        f"Failed to bind socket: {e},"
                        f" retrying in {retry_time} seconds."
                    )
                    time.sleep(retry_time)
            self.log.error("Failed to bind socket after 10 retries.")

    def _close_socket(self):
        if session.sessiontype == MAIN:
            self._sock.close()

    def _socket_recvfrom(self):
        if session.sessiontype == MAIN:
            try:
                return self._sock.recvfrom(1024)
            except socket.timeout:
                pass

        return None, None

    def _listen_for_packets(self):
        self.log.info("UDP listener thread started.")
        while not self._stop_event.is_set():
            self.log.info("Listening for UDP packets.")
            try:
                data, _ = self._socket_recvfrom()
                if not data:
                    continue
                message = data.decode("ascii", errors="ignore")
                message = re.sub(r"[^\x20-\x7E]+", "\x00", message)
                parts = [part for part in message.split("\x00") if part]
                pv_name = parts[1]
                with self._lock:
                    if pv_name not in self._pv_list:
                        self._pv_list.append(pv_name)
                        self.on_pnp_device_detected(pv_name)
                        self.log.info(
                            f"New PnP heartbeat received: {pv_name}. "
                            f"Adding to heartbeat list."
                        )
                self.log.info(f"Received UDP packet with pv_name: {pv_name}")

            except Exception as e:
                self.log.error(f"Error receiving UDP packet: {e}")

            time.sleep(1)

    def _send_heartbeats(self):
        self.log.info("Heartbeat thread started.")
        try:
            while not self._stop_event.is_set():
                self.log.info("Sending heartbeats.")
                with self._lock:
                    for pv_name in list(self._pv_list):
                        try:
                            current_value = pvget(pv_name)
                            self.log.info(
                                f"Current value of {pv_name}: {current_value}"
                            )
                            pvput(pv_name, current_value + 1)
                        except Exception as e:
                            self.log.warning(f"Failed updating {pv_name}: {e}")
                            self.on_pnp_device_removed(pv_name)
                            self._pv_list.remove(pv_name)
                time.sleep(2)
        except Exception as e:
            self.log.error(f"Heartbeat thread encountered an error: {e}")
        finally:
            self.log.info("Heartbeat thread stopped.")

    def _find_setup(self, pv_root):
        """
        Find the setup name from the PV root.
        The pv_root is the first part of the PV name like "foo:bar"
        """
        all_setups = session.getSetupInfo()
        for setup_name, setup_dict in all_setups.items():
            setup_pv_root = setup_dict.get("pnp_pv_root", None)
            if not setup_pv_root:
                continue

            if setup_pv_root == pv_root:
                return setup_name
        return None

    def _send_pnp_event(self, event, setup_name, description):
        session.pnpEvent(event, setup_name, description)

    def on_pnp_device_detected(self, pv_name):
        pv_root = ":".join(pv_name.split(":")[:2])
        self.log.info(f"New PnP device detected: {pv_root}")

        # Find the setup name from the PV name
        setup_name = self._find_setup(pv_root)
        self.log.info(f"Setup name: {setup_name}")

        self._send_pnp_event("added", setup_name, pv_name)

    def on_pnp_device_removed(self, pv_name):
        pv_root = ":".join(pv_name.split(":")[:2])
        self.log.info(f"PnP device removed: {pv_root}")

        # Find the setup name from the PV name
        setup_name = self._find_setup(pv_root)
        self.log.info(f"Setup name: {setup_name}")

        self._send_pnp_event("removed", setup_name, pv_name)

    def close(self):
        self.log.info("Closing UDPHeartbeatsManager.")
        self._stop_event.set()

        if self._listener_thread and self._listener_thread.is_alive():
            self.log.info("Waiting for listener thread to stop.")
            self._listener_thread.join()
            self.log.info("Listener thread stopped.")

        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self.log.info("Waiting for heartbeat thread to stop.")
            self._heartbeat_thread.join()
            self.log.info("Heartbeat thread stopped.")

        self.log.info("Closing socket.")
        self._close_socket()

        self.log.info("UDPHeartbeatsManager closed.")

    def doShutdown(self):
        self.close()
