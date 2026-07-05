#set page(width: 1760pt, height: 680pt, margin: 0pt, fill: rgb("f8fafc"))
#set text(size: 11pt, font: ("Arial", "sans-serif"))

#let icon(name, w: 1.2cm) = image("icons/" + name + ".svg", width: w)

#let component(ic, title, desc, bg: white, border: luma(200), w: 220pt, h: 80pt) = rect(
  fill: bg, stroke: 2pt + border, radius: 8pt, width: w, height: h, inset: 12pt,
  [
    #grid(
      columns: (1.5cm, 1fr),
      align: horizon + left,
      column-gutter: 12pt,
      icon(ic, w: 1.4cm),
      [
        *#text(size: 13pt, fill: border.darken(30%))[#title]* \
        #v(4pt)
        #text(size: 10pt, fill: luma(100))[#desc]
      ]
    )
  ]
)

#let place_node(x, y, content) = place(dx: x - 110pt, dy: y - 40pt, content)

#let hline(x1, x2, y, label) = {
  place(dx: x1, dy: y)[#line(start: (0pt,0pt), end: (x2 - x1, 0pt), stroke: 3pt + rgb("94a3b8"))]
  place(dx: x2 - 10pt, dy: y - 6pt)[#polygon(fill: rgb("94a3b8"), (0pt, 0pt), (0pt, 12pt), (10pt, 6pt))]
  place(dx: (x1 + x2)/2 - 52pt, dy: y - 10pt)[
    #rect(fill: white, stroke: 1.5pt + rgb("cbd5e1"), radius: 4pt, inset: 6pt, width: 90pt)[
      #align(center)[#text(size: 11pt, fill: rgb("475569"), weight: "bold")[#label]]
    ]
  ]
}

#let hline_bidir(x1, x2, y, label) = {
  place(dx: x1, dy: y)[#line(start: (0pt,0pt), end: (x2 - x1, 0pt), stroke: 3pt + rgb("94a3b8"))]
  place(dx: x2 - 10pt, dy: y - 6pt)[#polygon(fill: rgb("94a3b8"), (0pt, 0pt), (0pt, 12pt), (10pt, 6pt))]
  place(dx: x1, dy: y - 6pt)[#polygon(fill: rgb("94a3b8"), (10pt, 0pt), (10pt, 12pt), (0pt, 6pt))]
  place(dx: (x1 + x2)/2 - 70pt, dy: y - 10pt)[
    #rect(fill: white, stroke: 1.5pt + rgb("cbd5e1"), radius: 4pt, inset: 6pt, width: 100pt)[
      #align(center)[#text(size: 11pt, fill: rgb("475569"), weight: "bold")[#label]]
    ]
  ]
}

#let vline(x, y1, y2, label) = {
  place(dx: x, dy: y1)[#line(start: (0pt,0pt), end: (0pt, y2 - y1), stroke: 3pt + rgb("94a3b8"))]
  place(dx: x - 6pt, dy: y2 - 10pt)[#polygon(fill: rgb("94a3b8"), (0pt, 0pt), (12pt, 0pt), (6pt, 10pt))]
  place(dx: x - 50pt, dy: (y1 + y2)/2 - 13pt)[
    #rect(fill: white, stroke: 1.5pt + rgb("cbd5e1"), radius: 4pt, inset: 6pt, width: 90pt)[
      #align(center)[#text(size: 11pt, fill: rgb("475569"), weight: "bold")[#label]]
    ]
  ]
}

#let elbow_right(x1, y1, x2, y2, label) = {
  let x_mid = (x1 + x2) / 2
  place(dx: x1, dy: y1)[#line(start: (0pt,0pt), end: (x_mid - x1, 0pt), stroke: 3pt + rgb("94a3b8"))]
  place(dx: x_mid, dy: y1)[#line(start: (0pt,0pt), end: (0pt, y2 - y1), stroke: 3pt + rgb("94a3b8"))]
  place(dx: x_mid, dy: y2)[#line(start: (0pt,0pt), end: (x2 - x_mid, 0pt), stroke: 3pt + rgb("94a3b8"))]
  
  place(dx: x2 - 10pt, dy: y2 - 6pt)[#polygon(fill: rgb("94a3b8"), (0pt, 0pt), (0pt, 12pt), (10pt, 6pt))]
  
  place(dx: x_mid - 50pt, dy: (y1 + y2)/2 - 13pt)[
    #rect(fill: white, stroke: 1.5pt + rgb("cbd5e1"), radius: 4pt, inset: 6pt, width: 100pt)[
      #align(center)[#text(size: 11pt, fill: rgb("475569"), weight: "bold")[#label]]
    ]
  ]
}

#let elbow_bidir(x1, y1, x2, y2, label) = {
  let x_mid = (x1 + x2) / 2
  place(dx: x1, dy: y1)[#line(start: (0pt,0pt), end: (x_mid - x1, 0pt), stroke: 3pt + rgb("94a3b8"))]
  place(dx: x_mid, dy: y1)[#line(start: (0pt,0pt), end: (0pt, y2 - y1), stroke: 3pt + rgb("94a3b8"))]
  place(dx: x_mid, dy: y2)[#line(start: (0pt,0pt), end: (x2 - x_mid, 0pt), stroke: 3pt + rgb("94a3b8"))]
  
  place(dx: x2 - 10pt, dy: y2 - 6pt)[#polygon(fill: rgb("94a3b8"), (0pt, 0pt), (0pt, 12pt), (10pt, 6pt))]
  place(dx: x1, dy: y1 - 6pt)[#polygon(fill: rgb("94a3b8"), (10pt, 0pt), (10pt, 12pt), (0pt, 6pt))]
  
  place(dx: x_mid - 55pt, dy: (y1 + y2)/2 - 13pt)[
    #rect(fill: white, stroke: 1.5pt + rgb("cbd5e1"), radius: 4pt, inset: 6pt, width: 110pt)[
      #align(center)[#text(size: 11pt, fill: rgb("475569"), weight: "bold")[#label]]
    ]
  ]
}

// ==========================================
// BACKGROUND ZONES
// ==========================================

// Global Networks
#place(dx: 40pt, dy: 120pt)[
  #rect(fill: rgb("eff6ff"), stroke: 2pt + rgb("3b82f6"), radius: 12pt, width: 280pt, height: 170pt)[
    #place(dx: 20pt, dy: 20pt)[#text(size: 14pt, weight: "bold", fill: rgb("1d4ed8"))[Global Networks]]
  ]
]

// Edge Ground Station
#place(dx: 40pt, dy: 320pt)[
  #rect(fill: rgb("ecfdf5"), stroke: 2pt + rgb("10b981"), radius: 12pt, width: 280pt, height: 270pt)[
    #place(dx: 20pt, dy: 20pt)[#text(size: 14pt, weight: "bold", fill: rgb("065f46"))[Edge Ground Station]]
  ]
]

// Cloud VPS Stack
#place(dx: 380pt, dy: 100pt)[
  #rect(fill: rgb("f5f3ff"), stroke: 2pt + rgb("8b5cf6"), radius: 16pt, width: 960pt, height: 500pt)[
    #place(dx: 30pt, dy: 25pt)[
      #grid(
        columns: (auto, 1fr), column-gutter: 15pt, align: horizon,
        icon("docker", w: 1.6cm),
        [
          #text(size: 18pt, weight: "bold", fill: rgb("4c1d95"))[Cloud VPS] \
          #text(size: 12pt, fill: rgb("5b21b6"))[_Docker Compose Architecture_]
        ]
      )
    ]
  ]
]

// End Users
#place(dx: 1400pt, dy: 240pt)[
  #rect(fill: white, stroke: 2pt + rgb("64748b"), radius: 12pt, width: 260pt, height: 260pt)[
    #place(dx: 20pt, dy: 20pt)[#text(size: 14pt, weight: "bold", fill: rgb("334155"))[End Users - Web Dashboard]]
  ]
]

// ==========================================
// ARROWS (Placed behind nodes)
// ==========================================

#hline(290pt, 410pt, 220pt, "REST Polling")
#vline(180pt, 440pt, 480pt, "Raw IQ")
#hline(290pt, 410pt, 520pt, "MQTT (TLS)")

#elbow_right(630pt, 220pt, 750pt, 350pt, "Webhook")
#elbow_right(630pt, 520pt, 750pt, 390pt, "MQTT Sub")

#elbow_bidir(970pt, 350pt, 1090pt, 220pt, "Tensors / Scores")
#elbow_bidir(970pt, 390pt, 1090pt, 520pt, "Read / Write")

#hline_bidir(970pt, 1430pt, 370pt, "WSS (Duplex)")

// ==========================================
// NODES (Absolute Positioning)
// ==========================================

#place_node(180pt, 220pt, component("satnogs", "SatNOGS Database", "Historical telemetry archives", border: rgb("1d4ed8")))
#place_node(180pt, 400pt, component("antenna", "Antenna & SDR", "Captures live RF", border: rgb("10b981")))
#place_node(180pt, 520pt, component("python", "Decoder Pipeline", "Hex parsing to JSON", border: rgb("10b981")))

#place_node(520pt, 220pt, component("python", "wedjat_scheduler", "Cron: Fetch & Train", border: rgb("f59e0b")))
#place_node(520pt, 520pt, component("mqtt", "wedjat_broker", "Mosquitto (1883)", border: rgb("8b5cf6")))

#place_node(860pt, 370pt, component("fastapi", "AI Backend (FastAPI)", "Inference & Routing", border: rgb("3b82f6")))

#place_node(1200pt, 220pt, component("pytorch", "Inference Engine", "PyTorch VAE", border: rgb("8b5cf6")))
#place_node(1200pt, 520pt, component("postgresql", "wedjat_db", "TimescaleDB", border: rgb("0ea5e9")))

// SvelteKit is visually distinct inside the End Users box
#place(dx: 1560pt - 130pt, dy: 340pt - 60pt)[
  #rect(fill: rgb("f1f5f9"), stroke: none, radius: 8pt, width: 200pt, height: 200pt)[
    #align(center + horizon)[
      #icon("svelte", w: 3.6cm) \
      #v(2pt)
      #text(size: 14pt, weight: "bold")[SvelteKit UI] \
      #v(2pt)
      #text(size: 11pt, fill: luma(100))[Live Telemetry & Alerts]
    ]
  ]
]
