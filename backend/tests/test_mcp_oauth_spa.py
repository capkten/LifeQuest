"""Production-style SPA assets must never turn OAuth 404s into HTML 200s."""
import os
from pathlib import Path
import subprocess
import sys


def test_built_frontend_preserves_discovery_errors(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    (tmp_path / 'backend').symlink_to(backend, target_is_directory=True)
    dist = tmp_path / 'frontend' / 'dist'
    (dist / 'assets').mkdir(parents=True)
    (dist / 'index.html').write_text('<html>isolated SPA fixture</html>', encoding='utf-8')
    environment = {
        **os.environ,
        'PYTHONPATH': str(tmp_path / 'backend'),
        'PYTHONDONTWRITEBYTECODE': '1',
        'SECRET_KEY': 'isolated-oauth-spa-regression',
        'DATABASE_URL': 'sqlite:///' + str(tmp_path / 'startup.sqlite'),
        'MCP_AUTOSTART': 'false',
        'MCP_OAUTH_ENABLED': 'false',
    }
    script = '''
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
    page = client.get('/oauth/authorize?request_id=short-lived-fixture')
    assert page.status_code == 200 and 'isolated SPA fixture' in page.text
    for path in ('/.well-known/oauth-authorization-server', '/.well-known/oauth-protected-resource', '/.well-known/oauth-protected-resource/mcp/http', '/.well-known/unknown'):
        response = client.get(path)
        assert response.status_code == 404, (path, response.status_code)
        assert response.headers['content-type'].startswith('application/json')
print('SPA and OAuth discovery responses verified')
'''
    result = subprocess.run([sys.executable, '-c', script], cwd=tmp_path, env=environment, text=True, capture_output=True, encoding='utf-8', timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'SPA and OAuth discovery responses verified' in result.stdout
