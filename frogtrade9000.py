#!/usr/bin/env python3
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

import json, random, sys, os, re, argparse, traceback, statistics
from datetime import datetime, timezone, timedelta
from time import sleep
from itertools import cycle
import requests

import pandas as pd
import numpy as np

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
from rich.style import Style
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.rule import Rule

informative_coin="BTC"
stake_coin="USDT"
timeframes = ["15m", "1h", "4h", "1m", "5m"]
tfcycle = cycle(timeframes)

tags_config = {}
trades_config = {}
chart_config = {}
uniqclients = {}
tradeinfolist = []

indicators = [{"colname":"rsi","headername":"RSI","round_val":0}]

retfear = {}
prev_resp = None

## keyboard entry on linux won't work unless you're sudo
suderp = (sys.platform != "linux") or (sys.platform == "linux" and os.geteuid() == 0)

urlre = "^\[([a-zA-Z0-9]+)\]*([a-zA-Z0-9\-._~%!$&'()*+,;=]+)?:([ a-zA-Z0-9\-._~%!$&'()*+,;=]+)@?([a-z0-9\-._~%]+|\[[a-f0-9:.]+\]|\[v[a-f0-9][a-z0-9\-._~%!$&'()*+,;=:]+\]):([0-9]+)?"
dfmt = "%Y-%m-%d %H:%M:%S"

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

        # change profit chart and tag summary by bot
        if re.match("^([a-zA-Z]+)$", key.name):
            kn = key.name.upper()

            # change tag summary table
            tagsumm = tags_config['summmap']
            if kn in tagsumm:
                tags_config['current_summary'] = tagsumm[kn]

            # change profit chart
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

    current_config = client.show_config()
    bot_state = current_config['state']
    runmode = current_config['runmode']
    strategy = current_config['strategy']
    stoploss = abs(current_config['stoploss']) * 100
    max_open_trades = current_config['max_open_trades']
    stake_amount = current_config['stake_amount']
    
    stuff = (client, bot_state, runmode, stoploss, max_open_trades, stake_amount)
    
    print(f"Setting up {name} version {c['version']} at {server_url}: {strategy} {bot_state} {runmode}")
    sleep(1)
    
    if url not in uniqclients:
        uniqclients[url] = stuff
    
    return name, stuff

def make_layout(exclude_charts=False, include_sysinfo=False, include_candle_info=False, include_tag_summary=False, side_panel_minimum_size=114, num_days_daily=5) -> Layout:
    """Define the layout."""
    layout = Layout(name="root")

    layout.split(
        Layout(name="main", ratio=1),
        Layout(name="footer", size=1),
    )
    
    if exclude_charts:
        if include_sysinfo or include_tag_summary:
            layout["main"].split_row(
                Layout(name="left_side", minimum_size=side_panel_minimum_size),
                Layout(name="right_side", ratio=2),
            )

            if include_sysinfo and include_tag_summary:
                layout["right_side"].split(Layout(name="sys_info"), Layout(name="tag_summary"))
        else:
            layout["main"].split_row(
                Layout(name="left_side"),
            )
    else:
        layout["main"].split_row(
            Layout(name="left_side", minimum_size=side_panel_minimum_size),
            Layout(name="right_side", ratio=2),
        )
        
        if include_sysinfo:
            if include_candle_info:
                layout["right_side"].split(Layout(name="chart1", ratio=2), Layout(name="sys_info"), Layout(name="candle_info"))
            else:
                layout["right_side"].split(Layout(name="chart1"), Layout(name="sys_info"))
        else:
            layout["right_side"].split(Layout(name="chart1"), Layout(name="chart2"))
    
    layout["footer"].split_row(
        Layout(name="footer_clock", size=28),
        Layout(name="footer_left", ratio=2),
        Layout(name="footer_right", size=62)
    )

    layout["left_side"].split(
        Layout(name="open", ratio=2, minimum_size=8),
        Layout(name="closed", ratio=2, minimum_size=7),
        Layout(name="summary"),
        Layout(name="daily", size=(num_days_daily+7)))

    return layout

def make_candle_info_layout(exclude_charts=False, include_sysinfo=False, include_tag_summary=False, side_panel_minimum_size=114, num_days_daily=5) -> Layout:
    """Define the layout."""
    layout = Layout(name="root")

    layout.split(
        Layout(name="main", ratio=2),
        Layout(name="candle_info", ratio=1),
        Layout(name="footer", size=1),
    )    
    
    if exclude_charts:
        if include_sysinfo:
            layout["main"].split_row(
                Layout(name="left_side", minimum_size=side_panel_minimum_size),
                Layout(name="right_side", ratio=2),
            )

            layout["left_side"].split(
                Layout(name="open", minimum_size=8),
                Layout(name="closed", minimum_size=7),
            )
            
            layout["right_side"].split(
                Layout(name="summary"),
                Layout(name="daily", size=(num_days_daily+7)),
                Layout(name="sys_info"),
            )
        else:
            layout["main"].split_row(
                Layout(name="left_side"),
            )
    else:
        layout["main"].split_row(
            Layout(name="left_side", minimum_size=side_panel_minimum_size),
            Layout(name="right_side", ratio=2),
        )
        
        if include_sysinfo:
            layout["right_side"].split(Layout(name="chart1"), Layout(name="sys_info"))
        else:
            layout["right_side"].split(Layout(name="chart1"), Layout(name="chart2"))
    
        layout["left_side"].split(
            Layout(name="open", ratio=2, minimum_size=8),
            Layout(name="closed", ratio=2, minimum_size=7),
            Layout(name="summary"),
            Layout(name="daily", size=(num_days_daily+7)))
    
    layout["footer"].split_row(
        Layout(name="footer_clock", size=28),
        Layout(name="footer_left", ratio=2),
        Layout(name="footer_right", size=62)
    )

    return layout    

# thanks @rextea!
def fear_index(num_days_daily) -> Panel:
    default_resp = {
        "name": "Fear and Greed Index",
        "data": [
            {
                "value": "3",
                "value_classification": "Neutral",
                "timestamp": str(datetime.today()),
            }
        ]
    }
    
    if not retfear:
        resp = requests.get(f'https://api.alternative.me/fng/?limit={num_days_daily}&date_format=kr')
    else:
        if str(datetime.today()) in retfear:
            return retfear[str(datetime.today())]
        else:
            resp = requests.get('https://api.alternative.me/fng/?limit=1&date_format=kr')

    if resp is not None and resp.headers.get('Content-Type').startswith('application/json'):
        try:
            prev_resp = resp.json()
            df_gf = prev_resp['data']
        except:
            prev_resp = default_resp
            df_gf = prev_resp['data']
    else:
        prev_resp = default_resp
        df_gf = self.prev_resp['data']
    
    colourmap = {}
    colourmap['Extreme Fear'] = '[red]'
    colourmap['Fear'] = '[lightred]'
    colourmap['Neutral'] = '[yellow]'
    colourmap['Greed'] = '[lightgreen]'
    colourmap['Extreme Greed'] = '[green]'
    
    for i in df_gf:
        retfear[i['timestamp']] = f"{colourmap[i['value_classification']]}{i['value_classification']}"
    
    return retfear
    
def calc_risk(client):
    cl = client[0]
    max_open_trades = client[4]
    stake_amount = client[5]
    
    bal = cl.balance()
    avail_bal = 0
    for b in bal['currencies']:
        if b['currency'] == stake_coin:
            avail_bal = b['balance']
            break
    
    if max_open_trades > 0:
        max_capit = 0
        if stake_amount != "unlimited":
            max_capit = float(stake_amount * max_open_trades)
        else:
            max_capit = float(avail_bal / max_open_trades)

        if max_capit > 0:
            risk_per_trade = ((max_capit / max_open_trades) / max_capit) * 100
            return -np.round(avail_bal * risk_per_trade / 100, 2)
        else:
            return 0
    else:
        return 0
    
def sysinfo(client_dict) -> Panel:
    syslist = []
    
    for n, client in uniqclients.items():
        cl = client[0]
        progress_table = Table.grid(expand=True, pad_edge=True)
        
        progress_cpu = Progress(
            "{task.description}",
            BarColumn(bar_width=None, complete_style=Style(color="red"), finished_style=Style(color="red")),
            TextColumn("[red]{task.percentage:>3.0f}%"),
            expand=True,
        )
        
        progress_ram = Progress(
            "{task.description}",
            BarColumn(bar_width=None, complete_style=Style(color="magenta"), finished_style=Style(color="magenta")),
            TextColumn("[magenta]{task.percentage:>3.0f}%", style=Style(color="magenta")),
            expand=True,
        )
        
        progress_table.add_row(
            progress_cpu,
            progress_ram
        )

        si = cl.sysinfo()
        
        if 'cpu_pct' in si:
            for cpux in si['cpu_pct']:
                cpujob = progress_cpu.add_task("[cyan] CPU")
                progress_cpu.update(cpujob, completed=cpux)

            job2 = progress_ram.add_task("[cyan] RAM")
            progress_ram.update(job2, completed=si['ram_pct'])

            syslist.append(Rule(title=f"{n}", style=Style(color="cyan"), align="left"))
            syslist.append(progress_table)

    sysinfo_group = Group(*syslist)

    return Panel(sysinfo_group, title="[b]System Information", border_style="magenta")

def tradeinfo(client_dict, trades_dict, indicators) -> Table:
    yesterday = (datetime.now() - timedelta(days = 1)).strftime("%Y%m%d")
    
    table = Table(expand=True, box=box.HORIZONTALS)
    
    table.add_column("Pair", style="magenta", no_wrap=True, justify="left")
    table.add_column("Open", no_wrap=True, justify="right")
    table.add_column("Close", no_wrap=True, justify="right")
    table.add_column("Volume", no_wrap=True, justify="right")
    
    for ind in indicators:
        header_name = ind['headername']
        table.add_column(header_name, style="cyan", no_wrap=True, justify="left")
        
    shown_pairs = []
    
    for n, client in client_dict.items():
        cl = client[0]
        state = client[1]
        
        uparrow = "\u2191"
        downarrow = "\u2193"
        
        if isinstance(cl, ftrc.FtRestClient):
            if state == "running":
                open_trades = cl.status()
                if open_trades is not None:
                    for t in open_trades:
                        if t['pair'] not in shown_pairs:
                            try:
                                pairjson = cl.pair_candles(t['pair'], "5m", 2)
                                shown_pairs.append(t['pair'])
                                
                                if pairjson['columns'] and pairjson['data']:
                                    cols = pairjson['columns']
                                    data = pairjson['data']

                                    pairdf = pd.DataFrame(data, columns=cols)
                                    op = pairdf['open'].values[0]
                                    cl = pairdf['close'].values[0]
                                    candle_colour = "[green]"
                                    if op >= cl:
                                        candle_colour = "[red]"
                                    
                                    inds = []
                                    
                                    inds.append(f"{t['pair']}")
                                    inds.append(f"{candle_colour}{round(op, 3)}")
                                    inds.append(f"{candle_colour}{round(cl, 3)}")
                                    inds.append(f"{int(pairdf['volume'].values[0])}")
                                    
                                    for ind in indicators:
                                        df_colname = str(ind['colname'])
                                        round_val = ind['round_val']
                                        if df_colname in pairdf:
                                            curr_ind = pairdf[df_colname].values[0]
                                            prev_ind = pairdf[df_colname].values[1]

                                            trend = ""
                                            if prev_ind > curr_ind:
                                                trend = f"[red]{downarrow} "
                                            elif prev_ind < curr_ind:
                                                trend = f"[green]{uparrow} "
                                            else:
                                                trend = "[cyan]- "

                                            if round_val == 0:
                                                dval = int(curr_ind)
                                            else:
                                                dval = round(curr_ind, round_val)
                                            inds.append(f"{trend}[white]{dval}")
                                        else:
                                            inds.append("")
                                    
                                    table.add_row(
                                        *inds
                                    )
                                    # tc = get_trade_candle(pairdf, t['open_date'], t['pair'], "5m")
                            except Exception as e:
                                ## noone likes exceptions
                                #print(e)
                                pass

            closed_trades = trades_dict[n]
            do_stuff = True
            if closed_trades is not None and do_stuff == True:
                t = closed_trades[0]

                if t['pair'] not in shown_pairs:
                    try:
                        pairjson = cl.pair_candles(t['pair'], "5m", 2)
                        shown_pairs.append(t['pair'])

                        if pairjson['columns'] and pairjson['data']:
                            cols = pairjson['columns']
                            data = pairjson['data']

                            pairdf = pd.DataFrame(data, columns=cols)
                            op = pairdf['open'].values[0]
                            cl = pairdf['close'].values[0]
                            candle_colour = "[green]"
                            if op >= cl:
                                candle_colour = "[red]"

                            inds = []
                            inds.append(f"{t['pair']}")
                            inds.append(f"{candle_colour}{round(op, 3)}")
                            inds.append(f"{candle_colour}{round(cl, 3)}")
                            inds.append(f"{int(pairdf['volume'].values[0])}")
                            
                            for ind in indicators:
                                df_colname = str(ind['colname'])
                                round_val = ind['round_val']
                                if df_colname in pairdf:
                                    curr_ind = pairdf[df_colname].values[0]
                                    prev_ind = pairdf[df_colname].values[1]

                                    trend = ""
                                    if prev_ind > curr_ind:
                                        trend = f"[red]{downarrow} "
                                    elif prev_ind < curr_ind:
                                        trend = f"[green]{uparrow} "
                                    else:
                                        trend = "[cyan]- "
                                    
                                    if round_val == 0:
                                        dval = int(curr_ind)
                                    else:
                                        dval = round(curr_ind, round_val)
                                    inds.append(f"{trend}[white]{dval}")
                                else:
                                    inds.append("")
                            
                            table.add_row(
                                *inds
                            )
                    except Exception as e:
                        ## noone likes exceptions
                        #print(e)
                        pass
    
    return table

def enter_tag_summary(client_dict) -> Table:
    taglist = []

    summ = 'A'
    summmap = {}

    for n, client in client_dict.items():
        cl = client[0]
        
        table = Table(expand=True, box=box.HORIZONTALS, show_footer=False)

        table.add_column("Bot", style="yellow", no_wrap=True)
        table.add_column("Tag", style="white", justify="left", no_wrap=True)
        table.add_column("W/L", no_wrap=True)
        table.add_column("Avg Dur", justify="right", no_wrap=True)
        table.add_column("Avg Win Dur", justify="right", no_wrap=True)
        table.add_column("Avg Loss Dur", justify="right", no_wrap=True)
        table.add_column("Profit", justify="right", no_wrap=True)

        # get dict of bot to trades
        trades_by_tag = {}

        for at in cl.trades()['trades']:
            if at['enter_tag'] not in trades_by_tag:
                trades_by_tag[at['enter_tag']] = []
            
            trades_by_tag[at['enter_tag']].append(at)

        for tag, trades in trades_by_tag.items():
            t_profit = 0.0
            
            tot_trade_dur = 0
            avg_win_trade_dur = 0
            avg_loss_trade_dur = 0
            win_trade_dur = 0
            num_win = 0
            loss_trade_dur = 0
            num_loss = 0

            for t in trades:
                profit = float(t['profit_abs'])
                t_profit += profit
                tdur = (datetime.strptime(t['close_date'], dfmt) - datetime.strptime(t['open_date'], dfmt)).total_seconds()
                tot_trade_dur = tot_trade_dur + tdur
                
                if profit > 0:
                    win_trade_dur = win_trade_dur + tdur
                    num_win = num_win + 1
                else:
                    loss_trade_dur = loss_trade_dur + tdur
                    num_loss = num_loss + 1

            t_profit = round(t_profit, 2)

            avg_trade_dur = str(timedelta(seconds = round(tot_trade_dur / len(trades), 0)))
            if num_win > 0:
                avg_win_trade_dur = str(timedelta(seconds = round(win_trade_dur / num_win, 0)))
            if num_loss > 0:
                avg_loss_trade_dur = str(timedelta(seconds = round(loss_trade_dur / num_loss, 0)))

            table.add_row(
                f"{n}",
                f"[white]{tag}",
                f"[green]{num_win}/[red]{num_loss}",
                f"[yellow]{avg_trade_dur}",
                f"[green]{avg_win_trade_dur}",
                f"[red]{avg_loss_trade_dur}",
                f"[red]{t_profit}" if t_profit <= 0 else f"[green]{t_profit}",
            )

        summmap[summ] = n
        summ = chr(ord(summ) + 1)

        if n == tags_config['current_summary']:
            taglist.append(Rule(title=f"{n}", style=Style(color="blue"), align="left"))
            taglist.append(table)

    tag_group = Group(*taglist)

    tags_config['summmap'] = summmap

    return Panel(tag_group, title="[b]Enter Tag Summary", border_style="white")
    

def trades_summary(client_dict) -> Table:
    table = Table(expand=True, box=box.HORIZONTALS, show_footer=True)

    table.add_column("#", style="white", no_wrap=True)
    table.add_column("Bot", style="yellow", no_wrap=True)
    table.add_column("# Trades", no_wrap=True)
    table.add_column("Open Profit", style="blue", justify="right", no_wrap=True)
    table.add_column("W/L", justify="right", no_wrap=True)
    table.add_column("Winrate", justify="right", no_wrap=True)
    table.add_column("Exp.", justify="right", no_wrap=True)
    table.add_column("Exp. Rate", justify="right", no_wrap=True)
    table.add_column("Med. W", justify="right", no_wrap=True)
    table.add_column("Med. L", justify="right", no_wrap=True)
    table.add_column("Total", justify="right", no_wrap=True)
    
    summ = 'A'
    summmap = {}
    
    all_open_profit = 0
    all_profit = 0
    all_wins = 0
    all_losses = 0
    
    for n, client in client_dict.items():
        cl = client[0]
        
        itemcount = 1
        tot_profit = 0
        
        cls = cl.status()
        
        if cls is not None:
            for ot in cl.status():
                tot_profit = tot_profit + ot['profit_abs']
        
        max_open_trades = client[4]
        if (max_open_trades > 0):
            risk = calc_risk(client)
        
        tp = []
        tpw = []
        tpl = []
        for at in cl.trades()['trades']:
            profit = float(at['profit_abs'])
            tp.append(profit)
            if profit > 0:
                tpw.append(profit)
            else:
                tpl.append(abs(profit))
        
        mean_prof = 0
        mean_prof_w = 0
        mean_prof_l = 0
        median_prof = 0
        
        if len(tp) > 0:
            mean_prof = round(statistics.mean(tp), 2)
        
        if len(tpw) > 0:
            mean_prof_w = round(statistics.mean(tpw), 2)
            median_win = round(statistics.median(tpw), 2)
        else:
            mean_prof_w = 0
            median_win = 0
        
        if len(tpl) > 0:
            mean_prof_l = round(statistics.mean(tpl), 2)
            median_loss = round(statistics.median(tpl), 2)
        else:
            mean_prof_l = 0
            median_loss = 0
        
        if (len(tpw) == 0) and (len(tpl) == 0):
            winrate = 0
            loserate = 0
        else:
            winrate = (len(tpw) / (len(tpw) + len(tpl))) * 100
            loserate = 100 - winrate
        
        expectancy = 1
        if mean_prof_w > 0 and mean_prof_l > 0:
            expectancy = (1 + (mean_prof_w / mean_prof_l)) * (winrate / 100) - 1
        else:
            if mean_prof_w == 0:
                expectancy = 0
        
        expectancy_rate = ((winrate/100) * mean_prof_w) - ((loserate/100) * mean_prof_l)
                
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
            f"[cyan]{int(t['trade_count'])-int(t['closed_trade_count'])}[white]/[magenta]{t['closed_trade_count']}",
            f"[red]{round(tot_profit, 2)}" if tot_profit <= 0 else f"[green]{round(tot_profit, 2)}",            
            f"[green]{t['winning_trades']}/[red]{t['losing_trades']}",
            f"[cyan]{round(winrate, 1)}",
            f"[magenta]{round(expectancy, 2)}",
            f"[red]{round(expectancy_rate, 2)}" if expectancy_rate <= 0 else f"[green]{round(expectancy_rate, 2)}",
            # f"[red]{mean_prof}" if mean_prof <= 0 else f"[green]{mean_prof}",
            f"[green]{median_win}",
            f"[red]{median_loss}",
            f"[red]{pcc}" if pcc <= 0 else f"[green]{pcc}",
        )
        
        summmap[summ] = n
        
        summ = chr(ord(summ) + 1)
      
    table.columns[3].footer = f"[red]{round(all_open_profit, 2)}" if all_open_profit <= 0 else f"[green]{round(all_open_profit, 2)}"
    table.columns[4].footer = f"[green]{all_wins}/[red]{all_losses}"
    table.columns[10].footer = f"[red]{round(all_profit, 2)}" if all_profit <= 0 else f"[green]{round(all_profit, 2)}"

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
    table.add_column("S/L", justify="center")

    current_time = datetime.now(tz=timezone.utc)
    
    ## make sure we include the tzinfo
    fmt = "%Y-%m-%d %H:%M:%S%z"
    
    tradenum = 1
    tmap = {}
    
    for n, client in client_dict.items():
        cl = client[0]
        
        trades = cl.status()
        for t in trades:
            if 'buy_tag' in t.keys():
                if tradenum == 1:
                    table.add_column("Buy Tag", justify="right")
            
            ## force add the UTC time info
            ttime = datetime.strptime(f"{t['open_date']}+00:00", fmt)
            
            pairstr = t['pair'] + ('*' if (t['open_order_id'] is not None and t['close_rate_requested'] is None) else '') + ('**' if (t['close_rate_requested'] is not None) else '')
            t_dir = "S" if t['is_short'] else "L"

            if 'buy_tag' in t.keys():
                table.add_row(
                    f"{tradenum}",
                    f"{n}",
                    f"{t['strategy']}",
                    f"{pairstr}",
                    f"[red]{t['profit_pct']}" if t['profit_pct'] <= 0 else f"[green]{t['profit_pct']}",
                    f"[red]{round(t['profit_abs'], 2)}" if t['profit_abs'] < 0 else f"[green]{round(t['profit_abs'], 2)}",
                    f"{str(current_time-ttime).split('.')[0]}",
                    f"{t_dir}",
                    f"{t['buy_tag']}",
                )
            else:
                table.add_row(
                    f"{tradenum}",
                    f"{n}",
                    f"{t['strategy']}",
                    f"{pairstr}",
                    f"[red]{t['profit_pct']}" if t['profit_pct'] <= 0 else f"[green]{t['profit_pct']}",
                    f"[red]{t['profit_abs']}" if t['profit_abs'] < 0 else f"[green]{t['profit_abs']}",
                    f"{str(current_time-ttime).split('.')[0]}",
                    f"{t_dir}",
                )
            
            tmap[str(tradenum)] = t['pair']
            
            tradenum = tradenum+1
    
    trades_config['tmap'] = tmap
    trades_config['numopentrades'] = tradenum
    
    return table

def get_all_closed_trades(client_dict) -> dict:
    all_closed_trades = {}
    
    for n, client in client_dict.items():
        cl = client[0]
        
        ps = cl.profit()
        
        if ps is not None:
            num_all_closed_trades = int(ps['closed_trade_count'])

            m, r = divmod(int(num_all_closed_trades), 500)
            trades = []

            if m > 1:
                ## get last 500
                cltrades = cl.trades()
                if cltrades is not None and 'trades' in cltrades:
                    clt = cltrades['trades']
                    if clt is not None and len(clt) > 0:
                        trades.extend(clt)

                for i in range(1, m+1):
                    cltrades = cl.trades(offset=(500 * i))
                    if cltrades is not None and 'trades' in cltrades:
                        clt = cltrades['trades']
                        if clt is not None and len(clt) > 0:
                            trades.extend(clt)                        

            elif m == 1:
                cltrades = cl.trades()
                if cltrades is not None and 'trades' in cltrades:
                    clt = cltrades['trades']
                    if clt is not None and len(clt) > 0:
                        trades.extend(clt)                    

                cltrades = cl.trades(offset=500)
                if cltrades is not None and 'trades' in cltrades:
                    clt = cltrades['trades']
                    if clt is not None and len(clt) > 0:
                        trades.extend(clt)                    
            else:
                cltrades = cl.trades()
                if cltrades is not None and 'trades' in cltrades:
                    clt = cltrades['trades']
                    if clt is not None and len(clt) > 0:
                        trades = clt
            
            trades.reverse()
            all_closed_trades[n] = trades
    
    return all_closed_trades

def closed_trades_table(client_dict, trades_dict, num_closed_trades) -> Table:
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
    
    for n, client in client_dict.items():
        cl = client[0]
        
        if trades_dict:
            trades = trades_dict[n]
            if trades is not None:
                for t in trades[:num_closed_trades]:
                    otime = datetime.strptime(t['open_date'], fmt).astimezone(tz=timezone.utc)
                    ctime = datetime.strptime(t['close_date'], fmt).astimezone(tz=timezone.utc)
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

def daily_profit_table(client_dict, num_days_daily) -> Table:
    table = Table(expand=True, box=box.HORIZONTALS)

    table.add_column("Date", style="white", no_wrap=True)
    table.add_column("Fear", style="white", no_wrap=True)
    
    fear = fear_index(num_days_daily)
    
    for n, client in client_dict.items():
        cl = client[0]
        table.add_column(f"{n}", style="yellow", justify="right")
        table.add_column("#", style="cyan", justify="left")
    
    dailydict = {}
    
    for n, client in client_dict.items():
        cl = client[0]
        t = cl.daily(days=num_days_daily)
        for day in t['data']:
            if day['date'] not in dailydict.keys():
                dailydict[day['date']] = [day['date'], f"{fear[day['date']]}", f"{round(float(day['abs_profit']),2)} {t['stake_currency']}", f"{day['trade_count']}"]
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
    
def profit_chart(basic_chart, all_trades, height=20, width=120, limit=None, basic_symbols=False):
    # t = client.trades()['trades']
    if limit is not None:
        basic_chart.set_limit(limit)
    return basic_chart.get_profit_str(all_trades, height=height, width=width, basic_symbols=basic_symbols)
    
def get_real_chart_dims(console, header_size, side_panel_minimum_size, chart_panel_buffer_size=0):
    cdims = console.size
    ch = int(round(cdims.height/2) - header_size)
    cw = int(round(cdims.width - side_panel_minimum_size - chart_panel_buffer_size))
    return ch, cw

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose debugging mode")
    parser.add_argument("-c", "--config", nargs='?', help="Config to parse")
    parser.add_argument("-y", "--yaml", nargs='?', help="Supply a YAML file instead of command line arguments.")
    
    parser.add_argument("-s", "--servers", nargs='?', help="If you have multiple servers or your config differs from the REST API server URLs, specify each one here with [<name>@]<url>:<port> separated by a comma, e.g. mybotname@my.server:8081,my.server:8082,192.168.0.69:8083")
    parser.add_argument("-t", "--stake_coin", nargs="?", help="Stake coin. Default: USDT")
    parser.add_argument("-i", "--informative_coin", nargs="?", help="Informative coin. Default: BTC")
    parser.add_argument("-b", "--basic_symbols", action="store_true", help="Display non-rounded ASCII charts, for TTYs with poor fancy symbol support. Default: False")
    parser.add_argument("-x", "--exclude_charts", action="store_true", help="Do not draw charts, and expand sidebar to whole window. Default: False")
    parser.add_argument("-f", "--include_sysinfo", action="store_true", help="Include system information. If charts are also excluded, this will take up the full right pane. If not, it will replace the profit chart. Default: False")
    parser.add_argument("-k", "--include_candle_info", action="store_true", help="Include 5m candle information. Default: False")
    parser.add_argument("-o", "--include_tag_summary", action="store_true", help="Include summary of entry tags. Default: False")

    parser.add_argument("--debug", nargs="?", help="Debug mode")
    
    args = parser.parse_args()
    
    client_dict = {}
    
    config = args.config

    print(__doc__)
    
    if args.yaml is not None:
        import yaml
        with open(args.yaml, 'r') as yamlfile:
            args = dotdict(yaml.safe_load(yamlfile))
            args.yaml = True
    
    if "header_size" in args and args.header_size is not None:
        header_size = args.header_size
    else:
        header_size = 3
    
    if "side_panel_minimum_size" in args and args.side_panel_minimum_size is not None:
        side_panel_minimum_size = args.side_panel_minimum_size
    else:
        side_panel_minimum_size = 114
    
    if "num_days_daily" in args and args.num_days_daily is not None:
        num_days_daily = args.num_days_daily
    else:
        num_days_daily = 5

    if "num_closed_trades" in args and args.num_closed_trades is not None:
        num_closed_trades = args.num_closed_trades
    else:
        num_closed_trades = 2
    
    stake_coin = "USDT"
    if args.stake_coin is not None:
        stake_coin = args.stake_coin

    informative_coin = "BTC"
    if args.informative_coin is not None:
        informative_coin = args.informative_coin

    informative_pair = f"{informative_coin}/{stake_coin}"
    chart_config['current_pair'] = informative_pair

    if args.servers is not None:
        if args.yaml:
            indicators = args.indicators
            
            for s in args.servers:
                try:
                    if config is not None:
                        name, client = setup_client(name=botname, url=url, port=port, username=suser, password=spass, config_path=config)
                    else:
                        name, client = setup_client(name=s['name'], url=s['ip'], port=s['port'], username=s['username'], password=s['password'])
                    client_dict[name] = client
                except Exception as e:
                    raise RuntimeError('Cannot create freqtrade client') from e
        else:
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
                        raise RuntimeError("Cannot create freqtrade client") from e
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
    
    tags_config['current_summary'] = str(list(client_dict.keys())[0])

    chart_config['current_summary'] = str(list(client_dict.keys())[0])
    chart_config['current_timeframe'] = "5m"
    
    console = Console()
    ch, cw = get_real_chart_dims(console, header_size, side_panel_minimum_size)

    pc = bc.BasicCharts(symbol=chart_config['current_pair'], timeframe=chart_config['current_timeframe'], limit=cw)
    
    if args.exclude_charts and args.include_candle_info:
        layout = make_candle_info_layout(exclude_charts=args.exclude_charts, include_sysinfo=args.include_sysinfo, include_tag_summary=args.include_tag_summary, side_panel_minimum_size=side_panel_minimum_size, num_days_daily=num_days_daily)
    else:
        layout = make_layout(exclude_charts=args.exclude_charts, include_sysinfo=args.include_sysinfo, include_candle_info=args.include_candle_info, include_tag_summary=args.include_tag_summary, side_panel_minimum_size=side_panel_minimum_size, num_days_daily=num_days_daily)
    
    if not args.exclude_charts:
        layout["chart1"].update(Panel(Status("Loading...", spinner="line")))
        if not args.include_sysinfo:
            layout["chart2"].update(Panel(Status("Loading...", spinner="line")))
    
    if args.include_sysinfo:
        layout['sys_info'].update(Panel(Status("Loading...", spinner="line"), title="[b]System Information", border_style="magenta"))
    
    if args.include_candle_info:
        layout['candle_info'].update(Panel(Status("Loading...", spinner="line"), title="[b]Candle Information", border_style="cyan"))

    if args.include_tag_summary:
        layout['tag_summary'].update(Panel(Status("Loading...", spinner="line"), title="[b]Entry Tag Summary", border_style="white"))
    
    layout["open"].update(Panel(Status("Loading...", spinner="line"), title="Open Trades", border_style="green"))
    layout["summary"].update(Panel(Status("Loading...", spinner="line"), title="Trades Summary", border_style="red"))
    layout["daily"].update(Panel(Status("Loading...", spinner="line"), title="Daily Profit", border_style="yellow"))
    layout["closed"].update(Panel(Status("Loading...", spinner="line"), title="Closed Trades", border_style="blue"))
    
    layout["footer_clock"].update(datetime.now(tz=timezone.utc).ctime().replace(":", "[blink]:[/]") + " UTC")
    layout["footer_left"].update(" | Status: Loading...")
    layout["footer_right"].update(Text("frogtrade9000 by @froggleston [https://github.com/froggleston]", justify="right"))
    
    update_sec = 5
    updatenum = 0
    
    if args.debug:
        # print(get_all_closed_trades(client_dict).items())
        print("DEBUG MODE")
    else:
        with Live(layout, refresh_per_second=0.33, screen=True):
            if suderp:
                keyboard.on_press(key_press)
            
            while True:
                try:
                    updatenum = updatenum + 1
                    do_info_panels_update = False

                    if updatenum / update_sec == 1:
                        do_info_panels_update = True
                        updatenum = 0
                        
                    if (do_info_panels_update):
                        all_closed_trades = get_all_closed_trades(client_dict)

                        ch, cw = get_real_chart_dims(console, header_size, side_panel_minimum_size)

                        layout["summary"].size = 7+len(client_dict.items())
                        layout["summary"].update(Panel(trades_summary(client_dict), title="Trades Summary", border_style="red", height=7+len(client_dict.items())))

                        layout["daily"].update(Panel(daily_profit_table(client_dict, num_days_daily), title="Daily Profit", border_style="yellow", height=(num_days_daily+6)))
                        layout["closed"].update(Panel(closed_trades_table(client_dict, all_closed_trades, num_closed_trades), title="Closed Trades", border_style="blue"))
                    
                        if not args.exclude_charts:
                            spc = pair_chart(pc, height=ch-4, width=cw, limit=cw, timeframe=chart_config['current_timeframe'], basic_symbols=args.basic_symbols)

                            layout["chart1"].update(Panel(spc[1], title=f"{spc[0]} [{pc.get_timeframe()}]"))

                            if not args.include_sysinfo:
                                ppc = profit_chart(pc, all_closed_trades[chart_config['current_summary']], height=ch-4, width=cw, basic_symbols=args.basic_symbols)                            
                                layout["chart2"].update(Panel(ppc, title=f"{chart_config['current_summary']} Cumulative Profit"))
                            else:
                                if args.include_candle_info:
                                    layout["candle_info"].update(Panel(tradeinfo(client_dict, all_closed_trades, indicators), title="Recent Buy Info", border_style="cyan"))
                        else:
                            if args.include_candle_info:
                                layout["candle_info"].update(Panel(tradeinfo(client_dict, all_closed_trades, indicators), title="[b]Candle Information", border_style="cyan"))                
                    
                    layout["open"].update(Panel(open_trades_table(client_dict), title="Open Trades", border_style="green"))
                    
                    if args.include_sysinfo:
                        layout["sys_info"].update(sysinfo(client_dict))
                    
                    if args.include_tag_summary:
                        layout['tag_summary'].update(enter_tag_summary(client_dict))

                    layout["footer_clock"].update(datetime.now(tz=timezone.utc).ctime().replace(":", "[blink]:[/]") + " UTC")
                    layout["footer_left"].update(f" |[green] OK")
                except Exception as e:
                    if args.verbose:
                        traceback.print_exc()
                    layout["footer_left"].update(f" |[red] ERROR: {e}")

if __name__ == "__main__":
    try:
        main()

    except Exception as e:
        # traceback.print_exc()
        print()
        print("You got frogged:\n{} => '{}'".format(e, e.__cause__))
