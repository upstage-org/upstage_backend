#!/bin/bash

FILE="src/global_config/load_env.py"
PLACEHOLDER="{REPLACE_CIPHER_KEY}"

if grep -q "$PLACEHOLDER" "$FILE"; then
  KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

  ESCAPED_KEY=$(printf '%s' "$KEY" | sed -e 's/[\/&]/\\&/g')

  sed -i "s|$PLACEHOLDER|$ESCAPED_KEY|" "$FILE"
  # sed -i '' "s|$PLACEHOLDER|$ESCAPED_KEY|" "$FILE"  # For macOS


  echo "Replaced Cipher key with generated key: $KEY"
else
  echo "No placeholder found in $FILE. Skipping replacement."
fi
