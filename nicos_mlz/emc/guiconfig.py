"""NICOS GUI default configuration."""

main_window = docked(
    vsplit(
        panel("nicos.clients.gui.panels.status.ScriptStatusPanel"),
        panel("nicos.clients.gui.panels.console.ConsolePanel"),
    ),
    (
        "NICOS devices",
        panel(
            "nicos.clients.gui.panels.devices.DevicesPanel", icons=True, dockpos="right"
        ),
    ),
    (
        "Experiment Information and Setup",
        panel("nicos.clients.gui.panels.expinfo.ExpInfoPanel"),
    ),
)

windows = [
    window("Editor", "editor", panel("nicos.clients.gui.panels.editor.EditorPanel")),
    window("History", "find", panel("nicos.clients.gui.panels.history.HistoryPanel")),
    window("Logbook", "table", panel("nicos.clients.gui.panels.elog.ELogPanel")),
    window(
        "Log files", "table", panel("nicos.clients.gui.panels.logviewer.LogViewerPanel")
    ),
    window("Errors", "errors", panel("nicos.clients.gui.panels.errors.ErrorPanel")),
]

tools = [
    tool(
        "Report NICOS bug or request enhancement",
        "nicos.clients.gui.tools.bugreport.BugreportTool",
    ),
]
