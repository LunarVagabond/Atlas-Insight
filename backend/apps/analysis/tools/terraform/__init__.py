from ..base import ToolPlugin
from .analysis import analyze

plugin = ToolPlugin(
    name='Terraform',
    slug='terraform',
    category='iac',
    detect_files=('main.tf', 'variables.tf', 'outputs.tf'),
    detect_exts=('.tf',),
    detect_dirs=('.terraform',),
    analyze=analyze,
)
