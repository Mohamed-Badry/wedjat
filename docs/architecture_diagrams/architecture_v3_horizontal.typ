#set page(width: 1400pt, height: auto, margin: 0.5cm, fill: rgb("f8fafc"))
#set text(size: 11pt, font: ("Arial", "sans-serif"))

#let icon(name, w: 1.2cm) = image("icons/" + name + ".svg", width: w)

#let component(ic, title, desc, bg: white, border: luma(200), w: 220pt) = rect(
  fill: bg, stroke: 1.5pt + border, radius: 8pt, width: w, inset: 12pt,
  [
    #grid(
      columns: (1.5cm, 1fr),
      align: horizon + left,
      column-gutter: 15pt,
      icon(ic, w: 1.4cm),
      [
        *#text(size: 12pt, fill: border.darken(30%))[#title]* \
        #text(size: 9pt, fill: luma(100))[#desc]
      ]
    )
  ]
)

#let right-arrow(label) = align(center + horizon)[
  #rect(fill: white, stroke: 1pt + rgb("cbd5e1"), radius: 4pt, inset: 6pt)[
    #text(size: 10pt, weight: "bold", fill: rgb("64748b"))[#label]
  ] \
  #text(size: 32pt, fill: rgb("cbd5e1"))[→]
]

#let down-arrow(label) = align(center)[
  #rect(fill: white, stroke: 1pt + rgb("cbd5e1"), radius: 4pt, inset: 6pt)[
    #text(size: 10pt, weight: "bold", fill: rgb("64748b"))[#label]
  ]
  #v(-5pt)
  #text(size: 32pt, fill: rgb("cbd5e1"))[↓]
]


#align(center)[
  #grid(
    columns: (auto, auto, auto, auto, auto, auto, auto),
    align: center + horizon,
    column-gutter: 15pt,
    row-gutter: 30pt,
    
    // ROW 1: Offline / Background
    [
      #component("satnogs", "SatNOGS Global", "Telemetry Database", border: rgb("1d4ed8"))
    ],
    right-arrow("REST Polling"),
    [
      #component("python", "watchdog_scheduler", "Cron: Fetch & Train", border: rgb("f59e0b"))
    ],
    right-arrow("Webhook"),
    [
      #component("fastapi", "AI Backend (FastAPI)", "Normalizes SI Units", border: rgb("3b82f6"))
    ],
    right-arrow("Tensors"),
    [
      #component("pytorch", "Inference Engine", "PyTorch VAE", border: rgb("8b5cf6"))
    ],

    // ROW 2: Live Edge Pipeline
    [
      #rect(fill: rgb("ecfdf5"), stroke: 2pt + rgb("10b981"), radius: 12pt, inset: 15pt, width: 250pt)[
        #align(left)[#text(size: 14pt, weight: "bold", fill: rgb("065f46"))[Edge Ground Station]]
        #v(10pt)
        #component("antenna", "Antenna & SDR", "Captures RF", border: rgb("10b981"), w: 100%)
        #v(10pt)
        #component("python", "Decoder Pipeline", "Hex parsing", border: rgb("10b981"), w: 100%)
      ]
    ],
    right-arrow("Encrypted MQTT"),
    [
      #component("mqtt", "watchdog_broker", "Mosquitto (1883)", border: rgb("8b5cf6"))
    ],
    right-arrow("MQTT Sub"),
    [
      #down-arrow("JSON Storage")
    ],
    [], // empty spacer
    [
      #down-arrow("SQL Storage")
    ],

    // ROW 3: Storage & Presentation
    [], // empty under ground station
    [],
    [], // empty under broker
    [],
    [
      #component("postgresql", "watchdog_db", "TimescaleDB", border: rgb("0ea5e9"))
    ],
    right-arrow("WebSockets"),
    [
      #component("svelte", "watchdog_frontend", "SvelteKit Dashboard", border: rgb("e11d48"))
    ],
  )
]
