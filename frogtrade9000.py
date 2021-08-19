#!/usr/bin/env python

"""
███████╗██████╗  ██████╗  ██████╗████████╗██████╗  █████╗ ██████╗ ███████╗ █████╗  ██████╗  ██████╗  ██████╗
██╔════╝██╔══██╗██╔═══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗██╔═████╗██╔═████╗██╔═████╗
█████╗  ██████╔╝██║   ██║██║  ███╗  ██║   ██████╔╝███████║██║  ██║█████╗  ╚██████║██║██╔██║██║██╔██║██║██╔██║
██╔══╝  ██╔══██╗██║   ██║██║   ██║  ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝   ╚═══██║████╔╝██║████╔╝██║████╔╝██║
██║     ██║  ██║╚██████╔╝╚██████╔╝  ██║   ██║  ██║██║  ██║██████╔╝███████╗ █████╔╝╚██████╔╝╚██████╔╝╚██████╔╝
╚═╝     ╚═╝  ╚═╝ ╚═════╝  ╚═════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝ ╚════╝  ╚═════╝  ╚═════╝  ╚═════╝

A command-line freqtrade REST API client

Author: froggleston [https://github.com/froggleston]

Donations:
    BTC: bc1qxdfju58lgrxscrcfgntfufx5j7xqxpdufwm9pv
    ETH: 0x581365Cff1285164E6803C4De37C37BbEaF9E5Bb

Conception Date: August 2021

"""

from __future__ import print_function, unicode_literals

import json, random, sys, os, re, argparse
from datetime import datetime
from time import sleep

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

informative_pair = "BTC/USDT"
chart_config = {"current_pair":informative_pair}
trades_config = {}

## keyboard entry on linux won't work unless you're sudo
suderp = (sys.platform != "linux") or (sys.platform == "linux" and os.geteuid() == 0)

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

        #if escape is pressed make listening false and exit
        if key.name == "esc":
            os._exit(0)

def setup_client(name=None, config_path="config.json", url=None, port=None):
    if config_path is None:
        config_path = "config.json"
        
    config = ftrc.load_config(config_path)

    if url is None:
        url = config.get('api_server', {}).get('listen_ip_address', '127.0.0.1')
    
    if port is None:
        port = config.get('api_server', {}).get('listen_port', '8080')
    
    if name is None:
        name = f"{url}:{port}"
    
    username = config.get('api_server', {}).get('username')
    password = config.get('api_server', {}).get('password')

    server_url = f"http://{url}:{port}"

    client = ftrc.FtRestClient(server_url, username, password)
    
    return client

def make_layout() -> Layout:
    """Define the layout."""
    layout = Layout(name="root")

    layout.split(
        Layout(name="header", size=header_size),
        Layout(name="main", ratio=1),
        # Layout(name="footer", size=footer_size),
    )
    layout["main"].split_row(
        Layout(name="side", minimum_size=100),
        Layout(name="body", ratio=2),
    )
    layout["side"].split(Layout(name="box1"), Layout(name="box2"), Layout(name="box3"), Layout(name="box4"))
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
    table = Table(expand=True)

    table.add_column("#", style="white", no_wrap=True)
    table.add_column("Bot", style="yellow", no_wrap=True)
    table.add_column("# Trades", style="magenta")
    table.add_column("W/L", justify="center")
    table.add_column("Profit", justify="right")
    
    summ = 'A'
    summmap = {}
    
    for n, cl in client_dict.items():
        t = cl.profit()
        pcc = int(t['profit_closed_coin'])
        coin = t['best_pair'].split('/')[1]
        
        table.add_row(
            f"{summ}",
            f"{n}",
            f"{int(t['trade_count'])-int(t['closed_trade_count'])}/{t['closed_trade_count']}",
            f"[green]{t['winning_trades']}/[red]{t['losing_trades']}",
            f"[red]{pcc} [white]{coin}" if pcc <= 0 else f"[green]{pcc} [white]{coin}"
        )
        
        summmap[summ] = n
        
        summ = chr(ord(summ) + 1)

    trades_config['summmap'] = summmap        
        
    return table
    
def open_trades_table(client_dict) -> Table:
    table = Table(expand=True)
    
    table.add_column("#", style="white", no_wrap=True)
    table.add_column("Bot", style="yellow", no_wrap=True)
    table.add_column("Strat", style="cyan")
    table.add_column("Pair", style="magenta", no_wrap=True)
    table.add_column("Profit", justify="right")
    table.add_column("Dur.", justify="right")
    
    current_time = datetime.now()
    fmt = "%Y-%m-%d %H:%M:%S"
    
    tradenum = 1
    tmap = {}
    
    for n, cl in client_dict.items():
        trades = cl.status()
        for t in trades:
            ttime = datetime.strptime(t['open_date'], fmt)
            table.add_row(
                f"{tradenum}",
                f"{n}",
                f"{t['strategy']}",
                f"{t['pair']}",
                f"[red]{t['profit_pct']}" if t['profit_pct'] <= 0 else f"[green]{t['profit_pct']}",
                f"{str(current_time-ttime).split('.')[0]}"
            )
            
            tmap[str(tradenum)] = t['pair']
            
            tradenum = tradenum+1
    
    trades_config['tmap'] = tmap
    trades_config['numopentrades'] = tradenum
    
    return table

def closed_trades_table(client_dict) -> Table:
    table = Table(expand=True)
    
    table.add_column("ID", style="white", no_wrap=True)
    table.add_column("Bot", style="yellow", no_wrap=True)
    table.add_column("Strat", style="cyan")
    table.add_column("Pair", style="magenta", no_wrap=True)
    table.add_column("Profit %", justify="right")
    table.add_column("Profit", justify="right")
    table.add_column("Dur.", justify="right")
    
    fmt = "%Y-%m-%d %H:%M:%S"
    
    for n, cl in client_dict.items():
        trades = cl.trades()['trades']
        trades.reverse()
        for t in trades[:3]:
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
                f"{str(ctime-otime).split('.')[0]}"
            )
    
    return table

def daily_profit_table(client_dict) -> Table:
    table = Table(expand=True)

    table.add_column("Date", style="white", no_wrap=True)
    
    for n, cl in client_dict.items():
        table.add_column(f"{n}", style="yellow")
        table.add_column("#", style="cyan")
    
    dailydict = {}
    
    for n, cl in client_dict.items():
        t = cl.daily(days=9)
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

def pair_chart(basic_chart, height=20, width=120, limit=None):
    basic_chart.set_symbol(chart_config['current_pair'])
    if limit is not None:
        basic_chart.set_limit(limit)
    return (chart_config['current_pair'], basic_chart.get_chart_str(height=height, width=width))
    
def profit_chart(basic_chart, client, height=20, width=120, limit=None):
    t = client.trades()['trades']
    if limit is not None:
        basic_chart.set_limit(limit)
    return basic_chart.get_profit_str(t, height=height, width=width)

def search_box():
    cdims = console.size
    ch = int(round(cdims.height/2))
    return str(ch)

    
def main():

    parser = argparse.ArgumentParser()
    
    parser.add_argument("-c", "--config", nargs='?', help="Config to parse")
    parser.add_argument("-s", "--servers", nargs='?', help="If you have multiple servers or your config differs from the REST API server URLs, specify each one here with [<name>@]<url>:<port> separated by a comma, e.g. mybotname@my.server:8081,my.server:8082,192.168.0.69:8083")
    args = parser.parse_args()
    
    #if args.config is None:
    #    raise Exception("Please supply a config file with -c")
        
    config = args.config
    
    client_dict = {}
    
    if args.servers is not None:
        slist = args.servers.split(",")
        for s in slist:
            botsplit = s.split("@")
            if len(botsplit) == 2:
                botname = botsplit[0]
                url = botsplit[1].split(":")[0]
                port = botsplit[1].split(":")[1]
                
                client = setup_client(name=botname, config_path=args.config, url=url, port=port)
                client_dict[botname] = client
            elif len(botsplit) > 2:
                raise Exception("Cannot parse server option. Please use name_to_give_your_bot@servername.com:port")
            else:
                url = s.split(":")[0]
                port = s.split(":")[1]
                
                client = setup_client(config_path=args.config, url=url, port=port)
                client_dict[s] = client
    
    if not client_dict:
        raise Exception("No valid clients specified in config or --servers option")
    
    chart_config['current_summary'] = str(list(client_dict.keys())[0])
    
    console = Console()
    cdims = console.size
    ch = int(round(cdims.height/2)-header_size)
    cw = int(round(cdims.width/2))

    pc = bc.BasicCharts(symbol=chart_config['current_pair'], timeframe="5m", limit=cw)
    
    layout = make_layout()
    layout["header"].update(Header())
    layout["chart1"].update(Panel(Status("Loading...", spinner="line")))
    layout["chart2"].update(Panel(Status("Loading...", spinner="line")))
    layout["box1"].update(Panel(Status("Loading...", spinner="line"), title="Open Trades", border_style="green"))
    layout["box2"].update(Panel(Status("Loading...", spinner="line"), title="Trades Summary", border_style="red"))
    layout["box3"].update(Panel(Status("Loading...", spinner="line"), title="Daily Profit", border_style="yellow"))
    layout["box4"].update(Panel(Status("Loading...", spinner="line"), title="Closed Trades", border_style="blue"))

    with Live(layout, refresh_per_second=1, screen=True):
        if suderp:
            keyboard.on_press(key_press)
        
        while True:
            cdims = console.size
            ch = int(round(cdims.height/2)-header_size)
            cw = int(round(cdims.width/2))
            
            spc = pair_chart(pc, height=ch-4, width=cw)
            ppc = profit_chart(pc, client_dict[chart_config['current_summary']], height=ch-4, width=cw)
                               
            layout["chart1"].update(Panel(spc[1], title=f"{spc[0]} [{pc.get_timeframe()}]"))
            layout["chart2"].update(Panel(ppc, title=f"{chart_config['current_summary']} Cumulative Profit"))
            layout["box1"].update(Panel(open_trades_table(client_dict), title="Open Trades", border_style="green"))
            layout["box2"].update(Panel(trades_summary(client_dict), title="Trades Summary", border_style="red"))
            layout["box3"].update(Panel(daily_profit_table(client_dict), title="Daily Profit", border_style="yellow"))
            layout["box4"].update(Panel(closed_trades_table(client_dict), title="Closed Trades", border_style="blue"))
    
if __name__ == "__main__":
    try:
        main()
  
    except Exception as e:
        print("You got frogged: ", e)
