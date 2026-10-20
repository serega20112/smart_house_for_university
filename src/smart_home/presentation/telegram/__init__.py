"""Telegram presentation layer.

The bot transport lives in the infrastructure layer and asks the composition
root for the two callables it needs: one that runs a command and one that tells
an unlinked chat how to link itself. The wording of the answers comes from the
same composer the web interface uses, so the two channels can never disagree.
"""
