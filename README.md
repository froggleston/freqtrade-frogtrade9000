# frogtrade9000 - a command-line Rich client for the freqtrade REST API

I found FreqUI too cumbersome and slow on my Raspberry Pi 400 when running multiple instances of freqtrade bots. So I came up with a python Rich client:

It has very basic interactivity via the keyboard module which has cross-platform issues. I might consider porting this all to prompt-toolkit in the future, but not now.

![image](https://user-images.githubusercontent.com/1872302/130063115-1e0be16d-7f6b-4762-8730-6aaee2e91f78.png)

### Requirements

If you don't have freqtrade, get it [here](https://github.com/freqtrade/freqtrade/), and you'll satisfy most of the requirements. If not you'll need to pip install:

#### Existing Freqtrade install

If you're intending to copy the scripts into an existing freqtrade folder, you'll need to activate your venv (e.g. `source ./path/to/freqtrade/env/bin/activate`) and pip install:

- keyboard
- rich

#### Standalone

You'll need to activate your venv or use the global python environment, and pip install:

- numpy
- pandas
- ccxt
- python-rapidjson
- keyboard
- rich

### Installation

#### Existing venv Freqtrade install
Once cloned, copy the script files into your freqtrade/scripts folder. That's it!

#### Existing dockerised Freqtrade install
You need to add a COPY command into your freqtrade dockerfile to copy the scripts into the container and rebuild. Full instructions coming soon!

#### Standalone
You'll need the rest_client.py file from the core freqtrade repo and place it in the same folder that you put these files. Grab it from here:
https://github.com/freqtrade/freqtrade/blob/stable/scripts/rest_client.py

### Running

Running frogtrade9000 with no options will make it look for your `config.json` file and read in the `api_server` stanza from there, picking up the server IP, port, username and password:

> ./scripts/frogtrade9000.py

To specify a config use `-c`:

> ./scripts/frogtrade9000.py -c my-other.config.json

The nice thing about frogtrade9000 is that you can monitor multiple bots and strategies. If you run multiple bots with different IPs/ports use the `-s` flag to manually specify your own botname, the IP and ports and any username/password info of the freqtrade API servers separated by commas:

> ./scripts/frogtrade9000.py -s \[bot1\]user:pass@192.168.1.69:8081,\[bot2\]user:pass@127.0.0.1:8082

For simpler TTYs/terminals that cannot display curved symbols, use the `-b` option to use square edges so plots render correctly:

> ./scripts/frogtrade9000.py -s \[bot1\]user:pass@192.168.1.69:8081,\[bot2\]user:pass@127.0.0.1:8082 -b

**Note that your password has to be RFC compliant. You can use alphanumeric characters and `- . _ ~ % ! $ & ' ( ) * + , ; =`**

### Using frogtrade9000

There's not much to say. It uses the Rich library to provide a console view, so there isn't really any decent interactivity as part of that library. However, if the keyboard is working (see below) then you can:

- use the number keys to change the top OHCLV chart to whichever open pair your bot is trading, e.g. from the screenshot above, pressing `1` would change the chart to SHIB/USDT. Pressing `0` takes you back to BTC/USDT (or whatever informative pair you've specified in the code).
- use the letter keys to change the bottom profit chart based on whichever bots you're running, e.g. pressing `B` will take you to the bot running on `192.168.1.77:8082`
- use the PgUp key to cycle through the OHCLV chart timeframe (supports 1m, 5m, 15m, 1h, 4h)

### Known issues

- The `keyboard` module needs root/sudo on Linux to gain access to `/dev/input*`. You can run frogtrade9000 without sudo, but any of the hokey keyboard interactivity will be disabled.
- The display flickers on some terminals, e.g. git bash. I can't do anything about that.
- The exception handling is lame. This needs improvement.
- A JSON config file would help with more granular bot use and general tool settings, e.g. informative pair as default. I'll get round to this soon.

### Acknowledgements

The very cool ASCII charts are from https://github.com/kroitor/asciichart under the [MIT licence](https://github.com/kroitor/asciichart/blob/master/LICENSE.txt)
