#set page(width: 1200pt, height: auto, margin: 0.5cm, fill: rgb("f8fafc"))
#set text(font: ("Arial", "sans-serif"), size: 10pt)

#let icon(name, w: 1.2cm) = image("icons/" + name + ".svg", width: w)

#let container(name, title, desc, border_color) = rect(
  fill: white, stroke: 1.5pt + border_color, radius: 8pt, width: 260pt, inset: 12pt,
  grid(
    columns: (1.5cm, 1fr),
    align: horizon + left,
    icon(name, w: 1.3cm),
    [
      *#text(size: 12pt, fill: border_color)[#title]* \
      #text(size: 10pt, fill: luma(100))[#desc]
    ]
  )
)

#let right-arrow(label) = align(center + horizon)[
  #rect(fill: white, stroke: 1pt + rgb("cbd5e1"), radius: 4pt, inset: 6pt)[
    #text(size: 10pt, weight: "bold", fill: rgb("64748b"))[#label]
  ] \
  #text(size: 32pt, fill: rgb("cbd5e1"))[→]
]

#align(center)[
  #rect(fill: rgb("f1f5f9"), stroke: 2pt + rgb("94a3b8"), radius: 12pt, inset: 30pt, width: 1100pt)[
    #align(left)[
      #text(size: 18pt, weight: "bold", fill: rgb("334155"))[Docker Host (vps-wedjat)]
    ]
    #v(30pt)

    #grid(
      columns: (auto, auto, auto, auto, auto),
      align: center + horizon,
      column-gutter: 20pt,
      
      // TIER 1: Background & Data Services
      rect(fill: rgb("f8fafc"), stroke: 1.5pt + rgb("cbd5e1"), radius: 8pt, inset: 20pt, width: 300pt, height: auto)[
        #align(left)[#text(size: 14pt, weight: "bold", fill: rgb("475569"))[Background & Data Services]]
        #v(20pt)
        #align(center)[
          #grid(
            columns: (auto),
            row-gutter: 20pt,
            container("mqtt", "wedjat_broker", "Mosquitto (1883)", rgb("8b5cf6")),
            container("postgresql", "wedjat_db", "TimescaleDB (5432)", rgb("0ea5e9")),
            container("python", "wedjat_scheduler", "Cron: Fetch & Train", rgb("f59e0b"))
          )
        ]
      ],

      right-arrow("Internal Routing"),

      // TIER 2: Application
      rect(fill: rgb("eff6ff"), stroke: 1.5pt + rgb("3b82f6"), radius: 8pt, inset: 20pt, width: 300pt, height: auto)[
        #align(left)[#text(size: 14pt, weight: "bold", fill: rgb("2563eb"))[Application Tier]]
        #v(30pt)
        #align(center)[
          #container("fastapi", "wedjat_api", "FastAPI Core (Port 8000)", rgb("3b82f6"))
        ]
      ],

      right-arrow("REST / WSS"),

      // TIER 3: Presentation
      rect(fill: rgb("fff1f2"), stroke: 1.5pt + rgb("f43f5e"), radius: 8pt, inset: 20pt, width: 300pt, height: auto)[
        #align(left)[#text(size: 14pt, weight: "bold", fill: rgb("e11d48"))[Presentation Tier]]
        #v(30pt)
        #align(center)[
          #container("svelte", "wedjat_frontend", "SvelteKit UI (Port 5173)", rgb("e11d48"))
        ]
      ]
    )
    
    #v(40pt)
    
    // Shared Volumes Footer
    #rect(fill: white, stroke: 1.5pt + rgb("94a3b8"), radius: 8pt, inset: 20pt, width: 100%)[
      #align(center)[
        #text(size: 14pt, weight: "bold", fill: rgb("334155"))[Shared Docker Volumes]
        #v(20pt)
        #grid(
          columns: (1fr, 1fr, 1fr, 1fr),
          column-gutter: 20pt,
          align: center,
          [ *`./src`* \ #text(size: 11pt, fill: rgb("64748b"))[Live code mounts] ],
          [ *`./data`* \ #text(size: 11pt, fill: rgb("64748b"))[Raw & processed CSVs] ],
          [ *`./models`* \ #text(size: 11pt, fill: rgb("64748b"))[PyTorch `.pt` artifacts] ],
          [ *`timescaledb_data`* \ #text(size: 11pt, fill: rgb("64748b"))[PostgreSQL storage] ]
        )
      ]
    ]
  ]
]
