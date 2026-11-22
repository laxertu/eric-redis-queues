"""
Consumer side of a two-process check: loads a channel persisted by e2e_tests.load and delivers its messages.

Usage: python -m e2e_tests.run <channel id> <connection id>
"""
import asyncio
import sys

from eric_sse.exception import InvalidConnectionException, ItemNotFound, NoMessagesException

from e2e_tests.load import build_repository

try:
    channel_id, connection_id = sys.argv[1:3]
except ValueError:
    print(__doc__)
    sys.exit(1)

try:
    channel = build_repository().load_one(channel_id)
    connection = channel.get_connection(connection_id)
except ItemNotFound:
    print('Invalid channel id')
    sys.exit(1)
except InvalidConnectionException:
    print('Invalid connection id')
    sys.exit(1)

connection.listener.start()
while True:
    try:
        # Waits up to 1 second for each message, as a blocking consumer would
        msg = asyncio.run(channel.wait_next(connection_id, 1))
    except NoMessagesException:
        print('done')
        break
    print('DELIVERED', msg.type, msg.payload)
