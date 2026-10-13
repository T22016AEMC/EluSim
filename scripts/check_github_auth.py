"""Check only GitHub's standard credential helper; never print credentials."""
import subprocess,os,json
git='C:/Users/T22016/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe'
env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'never'}
try:
 result=subprocess.run([git,'credential','fill'],input='protocol=https\nhost=github.com\n\n',capture_output=True,text=True,env=env,timeout=20)
 available=result.returncode==0 and 'password=' in result.stdout
 print(json.dumps({'github_standard_credential_available':available,'exit_code':result.returncode}))
except subprocess.TimeoutExpired:print('{"github_standard_credential_available":false,"reason":"helper timeout"}')
