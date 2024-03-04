from os import path

from nicos import config
from nicos.guisupport.qt import QIcon

root_path = config.nicos_root
icons_path = path.join(root_path, 'resources', 'material', 'icons')


def get_icon(icon_name):
    return QIcon(path.join(icons_path, icon_name))