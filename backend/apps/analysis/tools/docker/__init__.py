from ..base import ToolPlugin
from .analysis import analyze

plugin = ToolPlugin(
    name='Docker',
    slug='docker',
    category='container',
    detect_files=(
        'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
        '.dockerignore', 'Dockerfile.dev', 'Dockerfile.prod',
        'compose.yml', 'compose.yaml',
    ),
    analyze=analyze,
)
