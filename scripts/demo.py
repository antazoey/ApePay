"""
A demo showing some accounts randomly creating, modifying, and cancelling streams
"""

import random
from datetime import timedelta

import click
from ape.cli import ConnectedProviderCommand, ape_cli_context

from apepay import StreamManager


@click.command(cls=ConnectedProviderCommand)
@ape_cli_context()
@click.option("-l", "--min-stream-life", default=0)
@click.option("-n", "--num-accounts", default=10)
@click.option("-b", "--num-blocks", default=1000)
@click.option("-m", "--max-streams", default=10)
@click.option("-c", "--create-stream", type=float, default=0.1)
@click.option("-f", "--fund-stream", type=float, default=0.7)
@click.option("-k", "--cancel-stream", type=float, default=0.2)
def cli(
    cli_ctx,
    min_stream_life,
    num_accounts,
    num_blocks,
    max_streams,
    create_stream,
    fund_stream,
    cancel_stream,
):
    # Initialize experiment
    deployer = cli_ctx.account_manager.test_accounts[-1]
    token = cli_ctx.local_project.TestToken.deploy(sender=deployer)
    sm = StreamManager(
        cli_ctx.local_project.StreamManager.deploy(
            deployer, min_stream_life, [], [token], sender=deployer
        )
    )

    # Wait for user to start the example SB app...
    click.secho(
        f"Please run `APEPAY_CONTRACT_ADDRESS={sm.address} silverback run bots.example:app`",
        fg="bright_magenta",
    )
    if not click.confirm("Start experiment?"):
        return

    # Make sure all accounts have some tokens
    accounts = cli_ctx.account_manager.test_accounts[:num_accounts]
    decimals = token.decimals()
    for account in accounts:
        token.DEBUG_mint(account, 10_000 * 10**decimals, sender=account)

    # 26 tokens per day
    starting_life = timedelta(minutes=5).total_seconds()
    starting_tokens = 26 * 10**decimals
    funding_amount = 2 * 10**decimals
    streams = {a.address: [] for a in accounts}

    while cli_ctx.chain_manager.blocks.head.number < num_blocks:
        payer = random.choice(accounts)

        # Do a little garbage collection
        for stream in streams[payer.address]:
            click.echo(f"{payer}:{stream.stream_id} - {stream.time_left}")
            if not stream.is_active:
                click.echo(f"Stream '{payer}:{stream.stream_id}' is expired, removing...")
                streams[payer.address].remove(stream)

        if len(streams[payer.address]) > 0:
            stream = random.choice(streams[payer.address])

            if token.balanceOf(payer) >= 10 ** (decimals + 1) and random.random() < fund_stream:
                click.echo(
                    f"Stream '{payer}:{stream.stream_id}' is being funded "
                    f"w/ {funding_amount / 10**decimals:.2f} tokens..."
                )
                token.approve(sm.address, funding_amount, sender=payer)
                stream.add_funds(funding_amount, sender=payer)

            elif random.random() < cancel_stream:
                click.echo(f"Stream '{payer}:{stream.stream_id}' is being cancelled...")
                stream.cancel(sender=payer)
                streams[payer.address].remove(stream)

        elif token.balanceOf(payer) < starting_tokens:
            continue

        elif len(streams[payer.address]) < max_streams and random.random() < create_stream:
            click.echo(f"'{payer}' is creating a new stream...")
            token.approve(sm.address, starting_tokens, sender=payer)
            stream = sm.create(token, int(starting_tokens / starting_life), sender=payer)
            streams[payer.address].append(stream)
            click.echo(f"Stream '{payer}:{stream.stream_id}' was created successfully.")