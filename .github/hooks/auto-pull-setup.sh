#!/bin/bash
# Setup automatic pull for Arctic Shadow Tracker
# This script creates a Git post-commit hook that pulls remote changes

HOOK_FILE=".git/hooks/post-commit"

cat > "$HOOK_FILE" << 'HOOK'
#!/bin/bash
# Auto-pull remote changes after local commits
# This keeps the local repo synced with GitHub Actions updates

echo "Checking for remote updates..."

# Fetch latest changes
git fetch origin main --quiet

# Check if remote has new commits
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "Remote has updates. Pulling changes..."
    git pull origin main --no-edit --quiet

    if [ $? -eq 0 ]; then
        echo "✓ Successfully synced with remote AIS data"
    else
        echo "⚠ Pull failed - manual resolution may be needed"
    fi
else
    echo "Local is up to date with remote"
fi
HOOK

chmod +x "$HOOK_FILE"
echo "✓ Post-commit hook installed at $HOOK_FILE"
echo "Local repo will now auto-pull after each commit"
