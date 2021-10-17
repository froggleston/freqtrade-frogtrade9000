# freqTUI - a terminal command-line Rich client user interface for the freqtrade REST API

I found FreqUI too cumbersome and slow on my Raspberry Pi 400 when running multiple instances of freqtrade bots. So I came up with a python Rich client - originally called frogtrade9000 but now renamed and pip installable!

It has very basic interactivity via the keyboard module which has cross-platform issues. I might consider porting this all to prompt-toolkit in the future, but not now.

![image](https://user-images.githubusercontent.com/1872302/130063115-1e0be16d-7f6b-4762-8730-6aaee2e91f78.png)

### Requirements

If you don't have freqtrade, get it [here](https://github.com/freqtrade/freqtrade/), and you'll satisfy most of the requirements. If not you'll need to pip install the following requirements.

#### Existing Freqtrade install

If you're intending to copy the scripts into an existing freqtrade folder, you'll need to activate your venv (e.g. `source ./path/to/freqtrade/env/bin/activate`) and pip install:

- keyboard
- rich
- psutil

#### Standalone

You'll need to activate your venv or use the global python environment, and `pip install -r requirements.txt` or manually install the following:

- numpy
- pandas
- ccxt
- python-rapidjson
- keyboard
- rich
- psutil

### Installation

#### Existing venv Freqtrade install
Once cloned, copy the script files into your freqtrade/scripts folder. That's it!

#### Existing dockerised Freqtrade install
You need to add a COPY command into your freqtrade dockerfile to copy the scripts into the container and rebuild. Full instructions coming soon!

#### Standalone
You'll need the rest_client.py file from the core freqtrade repo and place it in the same folder that you put these files. Grab it from here:
https://github.com/freqtrade/freqtrade/blob/stable/scripts/rest_client.py

### Configuration

The easiest way to configure freqTUI is with a YAML file. You can use a YAML file (see `example_frogtrade_config.yaml`) that contains the options you wish to run freqTUI with, including:

- multiple servers in the `servers` config
- indicators based on those in your strategy, in the `indicators` config - the `colname` property has to match the dataframe column name for the indicator, e.g. 'rsi' for `dataframe['rsi']`, 'macd' for `dataframe['macd']`, etc. You can use the headername property to set a simple name for longer indicator column names, e.g. 'E50' instead of `ema_500`
- general terminal properties, e.g. the number of rows to show in the Daily Profit table (`num_days_daily`), or the width of the left hand side panels (`side_panel_minimum_size`)
- number of closed trades to show per strategy (`num_closed_trades`)

### Running

The easiest way to run freqTUI is with the YAML file specified in Configuration:

> ./scripts/freqTUI.py -y frogtrade_config.yaml

Running frogtrade9000 with no options will make it look for your `config.json` file and read in the `api_server` stanza from there, picking up the server IP, port, username and password:

> ./scripts/freqTUI.py

To specify a config use `-c`:

> ./scripts/freqTUI.py -c my-other.config.json

The nice thing about frogtrade9000 is that you can monitor multiple bots and strategies. If you run multiple bots with different IPs/ports use the `-s` flag to manually specify your own botname, the IP and ports and any username/password info of the freqtrade API servers separated by commas:

> ./scripts/freqTUI.py -s \[bot1\]user:pass@192.168.1.69:8081,\[bot2\]user:pass@127.0.0.1:8082

For simpler TTYs/terminals that cannot display curved symbols, use the `-b` option to use square edges so plots render correctly:

> ./scripts/freqTUI.py -s \[bot1\]user:pass@192.168.1.69:8081,\[bot2\]user:pass@127.0.0.1:8082 -b

Other options include:
- exclude the pair and profit charts using the `-x` flag
- include system information from the system that the bot is running on using `-s` (this requires a freqtrade PR to the REST API that is not merged yet, so this isn't functional)
- include candle information from open trades (freqtrade REST API provides 5m candles) using `-k`

**Note that your password has to be RFC compliant. You can use alphanumeric characters and `- . _ ~ % ! $ & ' ( ) * + , ; =`**

### Using freqTUI

There's not much to say. The view updates every 5 seconds, except open trades and the sysinfo panels which update every second.

It uses the Rich library to provide a console view, so there isn't really any decent interactivity as part of that library. However, if the keyboard is working (see below) then you can:

- use the number keys to change the top OHCLV chart to whichever open pair your bot is trading, e.g. from the screenshot above, pressing `1` would change the chart to SHIB/USDT. Pressing `0` takes you back to BTC/USDT (or whatever informative pair you've specified in the code).
- use the letter keys to change the bottom profit chart based on whichever bots you're running, e.g. pressing `B` will take you to the bot running on `192.168.1.77:8082`
- use the PgUp key to cycle through the OHCLV chart timeframe (supports 1m, 5m, 15m, 1h, 4h)

### Known issues

- The `keyboard` module needs root/sudo on Linux to gain access to `/dev/input*`. You can run freqTUI without sudo, but any of the hokey keyboard interactivity will be disabled.
- The display flickers on some terminals, e.g. git bash. I can't do anything about that.
- The exception handling is lame. This needs improvement.
- A JSON config file would help with more granular bot use and general tool settings, e.g. informative pair as default. I'll get round to this soon.

### Acknowledgements

The very cool ASCII charts are from https://github.com/kroitor/asciichart under the [MIT licence](https://github.com/kroitor/asciichart/blob/master/LICENSE.txt)
