#!/usr/bin/env bash
# Configures Git to use version-controlled hooks from .githooks directory
git config core.hooksPath .githooks
echo "✅ Git hooks configured to use .githooks/"
