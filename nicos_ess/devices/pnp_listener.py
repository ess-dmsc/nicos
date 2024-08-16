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

from nicos.core import SIMULATION, POLLER
from nicos.utils import createThread
from nicos.core.device import Device, Param


class UDPHeartbeatsManager(Device):
    parameters = {
        "port": Param("UDP port to listen on", type=int, mandatory=True),
    }

    def doInit(self, mode):
        if mode == SIMULATION:
            return
        if mode == POLLER:
            return

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(("", self.port))
        self._stop_event = threading.Event()
        self._listener_thread = createThread("udp_thread", self._listen_for_packets)

    def doStart(self):
        self._stop_event.clear()
        if self._listener_thread is None:
            self._listener_thread = createThread("udp_thread", self._listen_for_packets)

    def doStop(self):
        self._stop_event.set()
        if self._listener_thread.is_alive():
            self._listener_thread.join()
            self._listener_thread = None
        self._sock.close()

    def _listen_for_packets(self):
        while not self._stop_event.is_set():
            try:
                data, _ = self._sock.recvfrom(1024)  # Buffer size 1024 bytes
                message = data.decode(
                    "ascii", errors="ignore"
                )  # Decode and ignore non-ASCII chars
                message = re.sub(
                    r"[^\x20-\x7E]+", "\x00", message
                )  # Replace non-printable characters with null
                parts = [
                    part for part in message.split("\x00") if part
                ]  # Split and remove empty parts

                self.log.info(f"Received parts: {parts}")
            except Exception as e:
                self.log.error(f"Error receiving UDP packet: {e}")

    def close(self):
        self.doStop()
        super().close()
