#!/bin/bash
eval "$(lpass show --notes obc_credentials | sed 's/^/export /')"
