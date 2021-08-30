#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
███████╗██████╗  ██████╗  ██████╗████████╗██████╗  █████╗ ██████╗ ███████╗ █████╗  ██████╗  ██████╗  ██████╗
██╔════╝██╔══██╗██╔═══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗██╔═████╗██╔═████╗██╔═████╗
█████╗  ██████╔╝██║   ██║██║  ███╗  ██║   ██████╔╝███████║██║  ██║█████╗  ╚██████║██║██╔██║██║██╔██║██║██╔██║
██╔══╝  ██╔══██╗██║   ██║██║   ██║  ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝   ╚═══██║████╔╝██║████╔╝██║████╔╝██║
██║     ██║  ██║╚██████╔╝╚██████╔╝  ██║   ██║  ██║██║  ██║██████╔╝███████╗ █████╔╝╚██████╔╝╚██████╔╝╚██████╔╝
╚═╝     ╚═╝  ╚═╝ ╚═════╝  ╚═════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝ ╚════╝  ╚═════╝  ╚═════╝  ╚═════╝

A command-line freqtrade REST API client

Author: froggleston [https://github.com/froggleston]
Licence: MIT [https://github.com/froggleston/freqtrade-frogtrade9000/blob/main/LICENSE]

Donations:
    BTC: bc1qxdfju58lgrxscrcfgntfufx5j7xqxpdufwm9pv
    ETH: 0x581365Cff1285164E6803C4De37C37BbEaF9E5Bb

Conception Date: August 2021

"""

from __future__ import print_function, unicode_literals

import json, random, sys, os, re, argparse, traceback
from datetime import datetime
from time import sleep
from itertools import cycle

import rest_client as ftrc
import basic_chart as bc

from urllib.request import urlopen

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.prompt import Prompt, IntPrompt
from rich.spinner import Spinner
from rich.status import Status
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

header_size = 3
side_panel_minimum_size = 104
chart_panel_buffer_size = 15

# number of closed trades to show per bot
num_closed_trades = 3

informative_coin="BTC"
stake_coin="USDT"
timeframes = ["15m", "1h", "4h", "1m", "5m"]
tfcycle = cycle(timeframes)

trades_config = {}
chart_config = {}

## keyboard entry on linux won't work unless you're sudo
suderp = (sys.platform != "linux") or (sys.platform == "linux" and os.geteuid() == 0)

urlre = "^\[([a-zA-Z0-9]+)\]*([a-zA-Z0-9\-._~%!$&'()*+,;=]+)?:([a-zA-Z0-9\-._~%!$&'()*+,;=]+)@?([a-z0-9\-._~%]+|\[[a-f0-9:.]+\]|\[v[a-f0-9][a-z0-9\-._~%!$&'()*+,;=:]+\]):([0-9]+)?"

if suderp:
    import keyboard

    def key_press(key):
        ## change chart pair
        if re.match("^(\d+)$", key.name):
            tmap = trades_config['tmap']
            if key.name == "0":
                chart_config['current_pair'] = informative_pair
            if key.name in tmap:
                chart_config['current_pair'] = tmap[key.name]

        # change profit chart
        if re.match("^([a-zA-Z]+)$", key.name):
            kn = key.name.upper()
            summmap = trades_config['summmap']
            if kn in summmap:
                chart_config['current_summary'] = summmap[kn]

        # change chart timeframe
        if key.name == "page up":
            chart_config['current_timeframe'] = next(tfcycle)
                
        #if escape is pressed make listening false and exit
        if key.name == "esc":
            os._exit(0)

def setup_client(name=None, config_path=None, url=None, port=None, username=None, password=None):
    if url is None:
        config = ftrc.load_config(config_path)
        url = config.get('api_server', {}).get('listen_ip_address', '127.0.0.1')
        port = config.get('api_server', {}).get('listen_port', '8080')
        
        if username is None and password is None:
            username = config.get('api_server', {}).get('username')
            password = config.get('api_server', {}).get('password')
    else:
        if config_path is not None:
            config = ftrc.load_config(config_path)
            
            if username is None and password is None:
                username = config.get('api_server', {}).get('username')
                password = config.get('api_server', {}).get('password')

    if name is None:
        name = f"{url}:{port}"
    
    server_url = f"http://{url}:{port}"

    client = ftrc.FtRestClient(server_url, username, password)
    
    c = client.version()
    if "detail" in c.keys() and (c["detail"] == 'Unauthorized'):
        raise Exception(f"Could not connect to bot [{url}:{port}]: Unauthorised")

    return name, client

def make_layout() -> Layout:
    """Define the layout."""
    layout = Layout(name="root")

    layout.split(
        Layout(name="header", size=header_size),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=1),
    )
    layout["main"].split_row(
        Layout(name="side", minimum_size=side_panel_minimum_size),
        Layout(name="body", ratio=2),
    )
    layout["footer"].split_row(
        Layout(name="footer_left"),
        Layout(name="footer_right")
    )

    layout["side"].split(
        Layout(name="open", ratio=2, minimum_size=8),
        Layout(name="closed", ratio=2, minimum_size=7),
        Layout(name="summary"),
        Layout(name="daily", size=15))

    layout["body"].split(Layout(name="chart1"), Layout(name="chart2"))
    return layout

class Header:
    """Display header with clock."""

    def __rich__(self) -> Panel:
        grid = Table.grid(expand=True)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="right")
        grid.add_row(
            "Frogtrade9000 - \"Froggin' Since 2021\"",
            datetime.now().ctime().replace(":", "[blink]:[/]"),
        )
        return Panel(grid, style="white on blue")

def trades_summary(client_dict) -> Table:
    table = Table(expand=True, box=box.HORIZONTALS, show_footer=True)

    table.add_column("#", style="white", no_wrap=True)
    table.add_column("Bot", style="yellow", no_wrap=True)
    table.add_column("# Trades", style="magenta")
    table.add_column("Open Profit", style="blue", justify="right")
    table.add_column("Profit", justify="right")
    table.add_column("W/L", justify="right")
    
    summ = 'A'
    summmap = {}
    
    all_open_profit = 0
    all_profit = 0
    all_wins = 0
    all_losses = 0
    
    for n, cl in client_dict.items():
        itemcount = 1
        tot_profit = 0
        for ot in cl.status():
            tot_profit = tot_profit + ot['profit_abs']
        
        t = cl.profit()
        pcc = round(float(t['profit_closed_coin']), 2)
        # coin = t['best_pair'].split('/')[1]
        coin = stake_coin
        
        all_open_profit = all_open_profit + tot_profit
        all_profit = all_profit + pcc
        all_wins = all_wins + t['winning_trades']
        all_losses = all_losses + t['losing_trades']
        
        table.add_row(
            f"{summ}",
            f"{n}",
            f"{int(t['trade_count'])-int(t['closed_trade_count'])}/{t['closed_trade_count']}",
            f"[red]{round(tot_profit, 2)} [white]{coin}" if tot_profit <= 0 else f"[green]{round(tot_profit, 2)} [white]{coin}",
            f"[red]{pcc} [white]{coin}" if pcc <= 0 else f"[green]{pcc} [white]{coin}",
            f"[green]{t['winning_trades']}/[red]{t['losing_trades']}",
        )
        
        summmap[summ] = n
        
        summ = chr(ord(summ) + 1)
        
    table.columns[3].footer = f"[red]{round(all_open_profit, 2)} [white]{coin}" if all_open_profit <= 0 else f"[green]{round(all_open_profit, 2)} [white]{coin}"
    table.columns[4].footer = f"[red]{all_profit} [white]{coin}" if all_profit <= 0 else f"[green]{all_profit} [white]{coin}"
    table.columns[5].footer = f"[green]{all_wins}/[red]{all_losses}"

    trades_config['summmap'] = summmap
        
    return table
    
def open_trades_table(client_dict) -> Table:
    table = Table(expand=True, box=box.HORIZONTALS)
    
    table.add_column("#", style="white", no_wrap=True)
    table.add_column("Bot", style="yellow", no_wrap=True)
    table.add_column("Strat", style="cyan")
    table.add_column("Pair", style="magenta", no_wrap=True)
    table.add_column("Profit %", justify="right")
    table.add_column("Profit", justify="right")
    table.add_column("Dur.", justify="right")

    current_time = datetime.now()
    fmt = "%Y-%m-%d %H:%M:%S"
    
    tradenum = 1
    tmap = {}
    
    for n, cl in client_dict.items():
        trades = cl.status()
        for t in trades:
            if 'buy_tag' in t.keys():
                if tradenum == 1:
                    table.add_column("Buy Tag", justify="right")

            ttime = datetime.strptime(t['open_date'], fmt)
            
            pairstr = t['pair'] + ('*' if (t['open_order_id'] is not None and t['close_rate_requested'] is None) else '') + ('**' if (t['close_rate_requested'] is not None) else '')
            
            if 'buy_tag' in t.keys():
                table.add_row(
                    f"{tradenum}",
                    f"{n}",
                    f"{t['strategy']}",
                    f"{pairstr}",
                    f"[red]{t['profit_pct']}" if t['profit_pct'] <= 0 else f"[green]{t['profit_pct']}",
                    f"[red]{round(t['profit_abs'], 2)}" if t['profit_abs'] < 0 else f"[green]{round(t['profit_abs'], 2)}",
                    f"{str(current_time-ttime).split('.')[0]}",
                    f"{t['buy_tag']}"
                )
            else:
                table.add_row(
                    f"{tradenum}",
                    f"{n}",
                    f"{t['strategy']}",
                    f"{pairstr}",
                    f"[red]{t['profit_pct']}" if t['profit_pct'] <= 0 else f"[green]{t['profit_pct']}",
                    f"[red]{t['profit_abs']}" if t['profit_abs'] < 0 else f"[green]{t['profit_abs']}",
                    f"{str(current_time-ttime).split('.')[0]}"
                )
            
            tmap[str(tradenum)] = t['pair']
            
            tradenum = tradenum+1
    
    trades_config['tmap'] = tmap
    trades_config['numopentrades'] = tradenum
    
    return table

def closed_trades_table(client_dict) -> Table:
    table = Table(expand=True, box=box.HORIZONTALS)
    
    table.add_column("ID", style="white", no_wrap=True)
    table.add_column("Bot", style="yellow", no_wrap=True)
    table.add_column("Strat", style="cyan")
    table.add_column("Pair", style="magenta", no_wrap=True)
    table.add_column("Profit %", justify="right")
    table.add_column("Profit", justify="right")
    table.add_column("Dur.", justify="right")
    table.add_column("Sell", justify="right")
    
    fmt = "%Y-%m-%d %H:%M:%S"
    
    for n, cl in client_dict.items():
        trades = cl.trades()['trades']
        trades.reverse()
        for t in trades[:num_closed_trades]:
            otime = datetime.strptime(t['open_date'], fmt)
            ctime = datetime.strptime(t['close_date'], fmt)
            rpfta = round(float(t['profit_abs']), 2)
            
            table.add_row(
                f"{t['trade_id']}",
                f"{n}",
                f"{t['strategy']}",
                f"{t['pair']}",
                f"[red]{t['profit_pct']}" if t['profit_pct'] <= 0 else f"[green]{t['profit_pct']}",
                f"[red]{rpfta}" if rpfta <= 0 else f"[green]{rpfta}",
                f"{str(ctime-otime).split('.')[0]}",
                f"{t['sell_reason']}"
            )
    
    return table

def daily_profit_table(client_dict) -> Table:
    table = Table(expand=True, box=box.HORIZONTALS)

    table.add_column("Date", style="white", no_wrap=True)
    
    for n, cl in client_dict.items():
        table.add_column(f"{n}", style="yellow", justify="right")
        table.add_column("#", style="cyan", justify="left")
    
    dailydict = {}
    
    for n, cl in client_dict.items():
        t = cl.daily(days=8)
        for day in t['data']:
            if day['date'] not in dailydict.keys():
                dailydict[day['date']] = [day['date'], f"{round(float(day['abs_profit']),2)} {t['stake_currency']}", f"{day['trade_count']}"]
            else:
                dailydict[day['date']].append(f"{round(float(day['abs_profit']),2)} {t['stake_currency']}")
                dailydict[day['date']].append(f"{day['trade_count']}")
    
    for day, vals in dailydict.items():
        table.add_row(
            *vals
        )
    
    return table

def pair_chart(basic_chart, height=20, width=120, limit=None, timeframe=None, basic_symbols=False):
    basic_chart.set_symbol(chart_config['current_pair'])
    if limit is not None:
        basic_chart.set_limit(limit)
        
    if timeframe is not None:
        basic_chart.set_timeframe(timeframe)
        
    return (chart_config['current_pair'], basic_chart.get_chart_str(height=height, width=width, basic_symbols=basic_symbols))
    
def profit_chart(basic_chart, client, height=20, width=120, limit=None, basic_symbols=False):
    t = client.trades()['trades']
    if limit is not None:
        basic_chart.set_limit(limit)
    return basic_chart.get_profit_str(t, height=height, width=width, basic_symbols=basic_symbols)
    
def get_real_chart_dims(console):
    cdims = console.size
    ch = int(round(cdims.height/2) - header_size)
    cw = int(round(cdims.width - side_panel_minimum_size - chart_panel_buffer_size))
    return ch, cw
    
def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument("-c", "--config", nargs='?', help="Config to parse")
    parser.add_argument("-s", "--servers", nargs='?', help="If you have multiple servers or your config differs from the REST API server URLs, specify each one here with [<name>@]<url>:<port> separated by a comma, e.g. mybotname@my.server:8081,my.server:8082,192.168.0.69:8083")
    parser.add_argument("-t", "--stake_coin", nargs="?", help="Stake coin. Default: USDT")
    parser.add_argument("-i", "--informative_coin", nargs="?", help="Informative coin. Default: BTC")
    parser.add_argument("-b", "--basic_symbols", action="store_true", help="Display non-rounded ASCII charts, for TTYs with poor fancy symbol support. Default: False")
    
    args = parser.parse_args()
    
    client_dict = {}
        
    config = args.config
    
    stake_coin = "USDT"
    if args.stake_coin is not None:
        stake_coin = args.stake_coin
    
    informative_coin = "BTC"
    if args.informative_coin is not None:
        informative_coin = args.informative_coin    
    
    informative_pair = f"{informative_coin}/{stake_coin}"
    chart_config['current_pair'] = informative_pair
    
    if args.servers is not None:
        slist = args.servers.split(",")
        for s in slist:
            m = re.match(urlre, s)
            if m:
                botname = m.group(1)
                suser = m.group(2)
                spass = m.group(3)
                url = m.group(4)
                port = m.group(5)
                
                if url is None or port is None:
                    raise Exception("Cannot get URL and port from server option. Please use [name]user:pass@servername:port")
                
                try:
                    if config is not None:
                        name, client = setup_client(name=botname, url=url, port=port, username=suser, password=spass, config_path=config)
                    else:
                        name, client = setup_client(name=botname, url=url, port=port, username=suser, password=spass)
                    client_dict[name] = client
                except Exception as e:
                    raise RuntimeError('Cannot create freqtrade client') from e
            else:
                raise Exception("Cannot parse server option. Please use [name]user:pass@servername:port")
    elif config is not None:
        try:
            name, client = setup_client(config_path=config)
            client_dict[name] = client
        except Exception as e:
            raise RuntimeError('Cannot create freqtrade client') from e
    
    if not client_dict:
        raise Exception("No valid clients specified in config or --servers option")
    
    chart_config['current_summary'] = str(list(client_dict.keys())[0])
    chart_config['current_timeframe'] = "5m"
    
    console = Console()
    ch, cw = get_real_chart_dims(console)

    pc = bc.BasicCharts(symbol=chart_config['current_pair'], timeframe=chart_config['current_timeframe'], limit=cw)
    
    layout = make_layout()
    layout["header"].update(Header())
    layout["chart1"].update(Panel(Status("Loading...", spinner="line")))
    layout["chart2"].update(Panel(Status("Loading...", spinner="line")))
    layout["open"].update(Panel(Status("Loading...", spinner="line"), title="Open Trades", border_style="green"))
    layout["summary"].update(Panel(Status("Loading...", spinner="line"), title="Trades Summary", border_style="red"))
    layout["daily"].update(Panel(Status("Loading...", spinner="line"), title="Daily Profit", border_style="yellow"))
    layout["closed"].update(Panel(Status("Loading...", spinner="line"), title="Closed Trades", border_style="blue"))
    layout["footer_left"].update("Status: Loading...")
    layout["footer_right"].update(Text("Written by @froggleston [https://github.com/froggleston]", justify="right"))

    with Live(layout, refresh_per_second=1, screen=True):
        if suderp:
            keyboard.on_press(key_press)
        
        while True:
            ch, cw = get_real_chart_dims(console)

            try:
                spc = pair_chart(pc, height=ch-4, width=cw, limit=cw, timeframe=chart_config['current_timeframe'], basic_symbols=args.basic_symbols)
                ppc = profit_chart(pc, client_dict[chart_config['current_summary']], height=ch-4, width=cw, basic_symbols=args.basic_symbols)
                
                layout["chart1"].update(Panel(spc[1], title=f"{spc[0]} [{pc.get_timeframe()}]"))
                layout["chart2"].update(Panel(ppc, title=f"{chart_config['current_summary']} Cumulative Profit"))

                layout["open"].update(Panel(open_trades_table(client_dict), title="Open Trades", border_style="green"))

                layout["summary"].size = 7+len(client_dict.items())
                layout["summary"].update(Panel(trades_summary(client_dict), title="Trades Summary", border_style="red", height=7+len(client_dict.items())))

                layout["daily"].update(Panel(daily_profit_table(client_dict), title="Daily Profit", border_style="yellow", height=14))
                layout["closed"].update(Panel(closed_trades_table(client_dict), title="Closed Trades", border_style="blue"))

                # layout["footer_left"].update(f"[green] OK {ch} x {cw} | {cp.__rich_measure__(console, console.options)[0]} x {cp.__rich_measure__(console, console.options)[1]}")
                layout["footer_left"].update(f"[green] OK")
            except Exception as e:
                layout["footer_left"].update(f"[red] ERROR: {e}")

if __name__ == "__main__":
    try:
        main()
  
    except Exception as e:
        traceback.print_exc()
        print("You got frogged: ", e)
