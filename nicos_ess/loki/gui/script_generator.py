"""LoKI Script Generator."""

from enum import Enum


class TransOrder(Enum):
    TRANSFIRST = 0
    SANSFIRST = 1
    TRANSTHENSANS = 2
    SANSTHENTRANS = 3
    SIMULTANEOUS = 4


class Script:
    def _get_temperature(self, temperature):
        if not temperature:
            return ""
        return f"move(temperature, {temperature})\n"

    def _get_command(self, command):
        if not command:
            return ""
        return f"{command}\n"

    def _do_trans(self, trans_duration, trans_duration_type):
        return f'do_trans({trans_duration}, "{trans_duration_type}")\n'

    def _do_sans(self, sans_duration, sans_duration_type):
        return f'do_sans({sans_duration}, "{sans_duration_type}")\n'

    def _do_simultaneous(self, sans_duration, sans_duration_type):
        return f'do_simultaneous({sans_duration}, "{sans_duration_type}")\n'

    def _start_sample(self, row_values):
        script = f'# Sample = {row_values["sample"]["name"]}\n'
        script += self._get_command(row_values.get("pre-command"))
        script += f'set_sample(\'{row_values["sample"]["name"]}\')\n'
        script += f'move(positioner, "{row_values["position"]}")\n'
        script += self._get_temperature(row_values.get("temperature"))
        return script

    def _finish_sample(self, row_values):
        return self._get_command(row_values.get("post-command")) + "\n"


class TransFirst(Script):
    def generate_script(
        self,
        table_data,
        trans_duration_type,
        sans_duration_type,
        trans_times,
        sans_times,
    ):
        script = ""
        for i in range(max(trans_times, sans_times)):
            if i < trans_times:
                for row_values in table_data:
                    script += self._start_sample(row_values)
                    script += self._do_trans(
                        row_values["trans_duration"], trans_duration_type
                    )
                    script += self._finish_sample(row_values)
            if i < sans_times:
                for row_values in table_data:
                    script += self._start_sample(row_values)
                    script += self._do_sans(
                        row_values["sans_duration"], sans_duration_type
                    )
                    script += self._finish_sample(row_values)
        return script


class SansFirst(Script):
    def generate_script(
        self,
        table_data,
        trans_duration_type,
        sans_duration_type,
        trans_times,
        sans_times,
    ):
        script = ""
        for i in range(max(trans_times, sans_times)):
            if i < sans_times:
                for row_values in table_data:
                    script += self._start_sample(row_values)
                    script += self._do_sans(
                        row_values["sans_duration"], sans_duration_type
                    )
                    script += self._finish_sample(row_values)
            if i < trans_times:
                for row_values in table_data:
                    script += self._start_sample(row_values)
                    script += self._do_trans(
                        row_values["trans_duration"], trans_duration_type
                    )
                    script += self._finish_sample(row_values)
        return script


class TransThenSans(Script):
    def generate_script(
        self,
        table_data,
        trans_duration_type,
        sans_duration_type,
        trans_times,
        sans_times,
    ):
        script = ""
        for i in range(max(trans_times, sans_times)):
            for row_values in table_data:
                script += self._start_sample(row_values)
                if i < trans_times:
                    script += self._do_trans(
                        row_values["trans_duration"], trans_duration_type
                    )
                if i < sans_times:
                    script += self._do_sans(
                        row_values["trans_duration"], sans_duration_type
                    )
                script += self._finish_sample(row_values)
        return script


class SansThenTrans(Script):
    def generate_script(
        self,
        table_data,
        trans_duration_type,
        sans_duration_type,
        trans_times,
        sans_times,
    ):
        script = ""
        for i in range(max(trans_times, sans_times)):
            for row_values in table_data:
                script += self._start_sample(row_values)
                if i < sans_times:
                    script += self._do_sans(
                        row_values["sans_duration"], sans_duration_type
                    )
                if i < trans_times:
                    script += self._do_trans(
                        row_values["trans_duration"], trans_duration_type
                    )
                script += self._finish_sample(row_values)
        return script


class Simultaneous(Script):
    def generate_script(
        self,
        table_data,
        trans_duration_type,
        sans_duration_type,
        trans_times,
        sans_times,
    ):
        script = ""
        for _ in range(sans_times):
            for row_values in table_data:
                script += self._start_sample(row_values)
                script += self._do_simultaneous(
                    row_values["sans_duration"], sans_duration_type
                )
                script += self._finish_sample(row_values)
        return script


class ScriptFactory:
    _scripts_by_trans_order = {
        TransOrder.TRANSFIRST: TransFirst,
        TransOrder.SANSFIRST: SansFirst,
        TransOrder.TRANSTHENSANS: TransThenSans,
        TransOrder.SANSTHENTRANS: SansThenTrans,
        TransOrder.SIMULTANEOUS: Simultaneous,
    }

    @classmethod
    def from_trans_order(cls, trans_order):
        if trans_order in cls._scripts_by_trans_order:
            return cls._scripts_by_trans_order[trans_order]()

        raise NotImplementedError(f"Unspecified trans order {trans_order.name}")
