#!/usr/bin/env bash
set -euo pipefail

KEY_PATH="${HOME}/.ssh/id_ed25519"
KEY_COMMENT="${1:-}"

if [[ -z "${KEY_COMMENT}" ]]; then
  KEY_COMMENT="$(git config --global user.email || true)"
fi

if [[ -z "${KEY_COMMENT}" ]]; then
  KEY_COMMENT="autopersona-$(hostname)"
fi

mkdir -p "${HOME}/.ssh"
chmod 700 "${HOME}/.ssh"

if [[ ! -f "${KEY_PATH}" ]]; then
  echo "No SSH key found at ${KEY_PATH}; creating one now."
  ssh-keygen -t ed25519 -C "${KEY_COMMENT}" -f "${KEY_PATH}"
else
  echo "Using existing SSH key: ${KEY_PATH}"
fi

chmod 600 "${KEY_PATH}"
chmod 644 "${KEY_PATH}.pub"

if command -v pbcopy >/dev/null 2>&1; then
  pbcopy < "${KEY_PATH}.pub"
  echo "Public key copied to clipboard."
else
  echo "pbcopy not found. Copy this public key manually:"
  cat "${KEY_PATH}.pub"
fi

echo
echo "Open GitHub SSH settings and paste the copied key:"
echo "https://github.com/settings/keys"
echo
echo "After saving it on GitHub, test with:"
echo "ssh -T git@github.com"
echo
echo "Then push AutoPersona with:"
echo "cd /Users/etahn/Documents/Codex/2026-09-12/new-chat/AutoPersona"
echo "git push -u origin main"
