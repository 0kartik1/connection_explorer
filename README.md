**Unhinger** is a highly vibe-coded Python application built to completely unhinge the way you network.

Stop relying on awkward small talk. Unhinger takes the scattered information you currently have about a person, throws it into a discovery engine, and spits out the most optimal, borderline-obsessive (but socially acceptable) vectors for connection. Whether you're trying to find a mutual hyper-fixation, map out a conversation tree, or just find the perfect icebreaker, Unhinger has your back.

-----

## 🛠️ Tech Stack & Base Technologies

Unhinger is built on a lightweight, rock-solid Python foundation utilizing the classic MVC (Model-View-Controller) and Repository patterns.

  * **Language:** Pure Python 3.8+ 🐍
  * **Web Framework:** Python-based micro-framework (designed around `app.py` and `run.py` server architectures, commonly aligned with Flask or FastAPI).
  * **Data Persistence:** \* **ORM / Database:** Managed via `db.py` and `models/`, ensuring structured relational data storage.
      * **Data Access:** Handled through the Repository Pattern (`repository.py` and `crud.py`) to keep database queries entirely separate from business logic.
  * **Frontend / Templating:** Server-side rendered UI utilizing standard HTML/CSS/JS served from the `static/` directory and injected via the `templates/` folder (Jinja2 or similar templating engine).
  * **Core Logic:** Custom `discovery` engine that processes text/data inputs to output connection pathways.

-----

## ⚡ Quickstart

Get Unhinger up and running on your local machine before your next social interaction.

### Prerequisites

  * Python 3.8 or higher
  * `pip` (Python package manager)

### Installation

1.  **Clone the chaos:**

    ```bash
    git clone https://github.com/0kartik1/connection_explorer.git
    cd connection_explorer
    ```

2.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure the environment:**
    Set up your database URI and API keys (if using external LLMs/search tools for discovery) inside `.env` or `config.py`.

4.  **Run the application:**

    ```bash
    python run.py
    ```

    The server will boot up. Open your browser and navigate to the local host address provided in the terminal.

-----

## 🏗️ Architecture: Controlled Chaos

Unhinger keeps its unhinged goals neatly organized inside a strict, scalable architecture.

```text
connection_explorer/
├── 📁 controllers/    # Route handlers bridging the UI and the discovery engine
├── 📁 discovery/      # The "Brain" - Algorithms parsing info into conversation vectors
├── 📁 models/         # Database schemas mapping out entities and connection points
├── 📁 static/         # CSS stylesheets and vanilla JS for the frontend vibe
├── 📁 templates/      # HTML layouts rendering the connection pathways
├── 📄 app.py          # App initialization and middleware config
├── 📄 config.py       # Environment variables and app-wide settings
├── 📄 crud.py         # Standard Create/Read/Update/Delete operations
├── 📄 db.py           # Database connection pooling and session management
├── 📄 display.py      # Output formatting (making raw data look pretty)
├── 📄 repository.py   # Data abstraction layer (because direct DB calls are a sin)
├── 📄 requirements.txt# Project dependencies
└── 📄 run.py          # The ignition switch
```

-----

## 🧠 The "Unhinged" Process (How it Works)

1.  **The Brain Dump:** You input raw, disjointed context into the Unhinger UI—LinkedIn headlines, shared cities, random hobbies, or overlapping tech stacks.
2.  **The Discovery Phase:** The `/discovery` engine processes this data, filtering it through your local data stores (`repository.py`), looking for intersections.
3.  **The Output (`display.py`):** Unhinger renders an intuitive, visual map (or list) of high-probability connection angles on the frontend, giving you the exact talking points you need to seamlessly initiate contact.

-----

## 🎨 Why "Vibe Coded"?

Unhinger wasn't over-engineered in a corporate boardroom. It was *vibe coded*.

  * **Intuitive:** The folder structure makes sense the moment you look at it.
  * **Extensible:** Want to hook up a new AI model to the `discovery` folder? Go for it. The Repository pattern ensures you won't break the database while doing it.
  * **Fun:** It takes a stressful task (networking) and gamifies it.

-----

## 🤝 Contributing

Have a wild idea for a new connection algorithm? We want it.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/UnhingedIcebreaker`)
3.  Commit your Changes (`git commit -m 'Add dangerously effective icebreaker logic'`)
4.  Push to the Branch (`git push origin feature/UnhingedIcebreaker`)
5.  Open a Pull Request

-----

## 📝 License

Distributed under the MIT License. Use responsibly
