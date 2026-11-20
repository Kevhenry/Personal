# Garage Door Controller (ESP32-C3 SuperMini + ESPHome)

Opens and closes a LiftMaster/Chamberlain garage door from Home Assistant, and
shows whether the door is open or closed.

How it works: the wall button on your opener is just a switch that connects two
wires. The ESP32 drives a small relay wired in parallel with that button, so a
relay click is the same as someone pressing the button. A magnetic reed switch
on the door tells you whether it's actually closed.

> **Check first:** this works for openers whose **Learn button is purple, red,
> orange or green**. A **yellow** Learn button (Security+ 2.0) won't respond
> to a simple relay; that needs a different approach.

## Parts (~$15 total)

| Part | Notes |
| --- | --- |
| ESP32-C3 SuperMini | The board this config is written for |
| 1-channel relay module, **3.3V** (or 5V with a "high/low trigger" jumper set to **high**) | Low-trigger 5V modules may not switch off reliably from a 3.3V pin |
| Magnetic reed switch, normally open (the "door/window alarm sensor" kind) | Wired type, with screw terminals or leads |
| USB-C power supply (5V, 1A is plenty) + cable | Plug into the outlet the opener uses |
| 2-conductor bell/thermostat wire (18–22 AWG) | Long enough to reach from the opener to the door frame |
| Small project box (optional) | Keeps dust and spiders out |

## Wiring

| From | To |
| --- | --- |
| SuperMini **3V3** | Relay **VCC** |
| SuperMini **GND** | Relay **GND** |
| SuperMini **GPIO4** | Relay **IN** |
| SuperMini **GPIO3** | Reed switch wire 1 |
| SuperMini **GND** (any GND pin) | Reed switch wire 2 |
| Relay **COM** | Opener wall-button terminal #1 |
| Relay **NO** | Opener wall-button terminal #2 |

(If you use a 5V relay module, take VCC from the SuperMini's **5V** pin instead
of 3V3.)

1. **Relay → opener.** On the back of the opener motor are the push-in
   terminals where the existing wall-button wires go (usually red + white, or
   white + gray). Connect the relay's **COM** and **NO** to those **same two
   terminals**, alongside the existing wires. Polarity doesn't matter. Leave
   your wall button connected; both will work.
2. **Reed switch.** Mount the switch on the door frame and the magnet on the
   door so they line up (within ~1/2") **when the door is fully closed**. Run
   the two wires to **GPIO3** and **GND**. No resistor needed; the ESP32's
   internal pull-up handles it.
3. **Power.** USB-C into the SuperMini.

**Test before you wire it in:** briefly touch a piece of wire across the two
opener terminals. If the door moves, the relay approach will work.

## Flashing

1. Install ESPHome: `pip install esphome` (or use the ESPHome add-on in Home
   Assistant).
2. Copy `secrets.example.yaml` to `secrets.yaml` and fill it in. Generate the
   API key with `openssl rand -base64 32`. `secrets.yaml` is gitignored, so
   don't commit it.
3. Plug the SuperMini into your computer with USB-C and run:
   ```
   esphome run garage-door.yaml
   ```
   If it isn't detected, hold **BOOT**, tap **RESET**, release **BOOT**, then try
   again.
4. After the first flash, updates go over Wi-Fi: `esphome run garage-door.yaml`
   and pick the network option.

## Home Assistant

Home Assistant will discover **Garage Door** automatically (Settings → Devices &
Services). Paste the API key from `secrets.yaml` when it asks. You'll get:

- **Garage Door** – a proper garage-door entity with Open / Close buttons
  (it only presses the button if that would move the door the right way)
- **Garage Door Button** – a raw "press the wall button" control
- **Garage Door Closed** – the reed switch state
- Wi-Fi signal and uptime (diagnostics)

There's also a backup control page at `http://garage-door.local` (login
`admin` + your `web_password`) that works even if Home Assistant is down.

If it can't reach your Wi-Fi it starts its own network called
**Garage-Door Fallback**; connect to it to enter new Wi-Fi details.

## Notes & safety

- The door only knows "closed" or "not closed". While it's moving it reports
  open. Good enough for "did I leave it open?" and automations.
- Remote closing means nobody is watching the door. Your opener's safety
  sensors (the photo-eyes at the bottom of the track) still stop and reverse it
  if something's in the way. Keep them working.
- A handy automation: notify you if the door has been open more than 15
  minutes, or when everyone has left home.
- Wi-Fi drops? The config already lowers TX power, a known fix for SuperMini
  antennas. If it's still flaky, move the board out of the metal opener housing.
