from nicos.clients.gui.client import NicosGuiClient
from nicos.clients.gui.panels.base import SetupDepPanelMixin
from nicos.clients.gui.utils import DlgUtils
from nicos.guisupport.qt import QMainWindow
from nicos_ess.gui.mainwindow import MainWindow
from nicos_ess.gui.panels.panel import PanelBase
from nicos_ess.gui.panels.samples import SampleTablePanel

# def get_samples_test_double():
#     samples = [
#         {'weight': 11, 'Notes': '', 'name': 'samp1'},
#         {'weight3': 5, 'Notes': '', 'name': 'samp2'},
#         {'name': 'ads'}
#     ]
#     return samples


class TestSamplePanel:
    def test(self):
        panel = SampleTablePanel(
            parent=QMainWindow(), client=NicosGuiClient, options=DlgUtils
        )
        assert True

    # def test_add_samples_from_sample_device_to_table(self):
    #     panel = SampleTablePanel()
    #     samples = test_double_get_samples()
    #     panel.load_samples(samples)
    #     assert (
    #         len(panel.table.model.raw_data) == 3 and
    #         True
    #     )

    # Add samples from csv to table
    # Write samples to csv table
    # Add column to table
    # Remove column from table
    # Add empty row to table
    # Add copied row to table
    # Remove row from table
    # Rename column in table
    # Make edits inside table
    # Save changes to Sample device
    # Discard changes and show existing info from Sample device
