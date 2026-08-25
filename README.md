# swiss-referendum-visualization
Exploratory Data Analysis and Visualization of Swiss Referendums (1880–2023)
# Swiss Referendums: Interactive Data Visualization & Topic Analysis (1880–2023)

An interactive Streamlit web application exploring historical voting patterns, voter turnout, and geographic trends in Swiss popular initiatives and referendums.

Developed by **Flora Gashi** and **Sevan Sherbetjian** as part of the Data Visualization module (B.Sc. Artificial Intelligence & Machine Learning) at Lucerne University of Applied Sciences and Arts (HSLU).

---

## Key Features & Insights

* **Interactive Streamlit Dashboard:** Allows users to filter historical voting data by key topics and timeframes.
* **Topic Identification via NLP:** Applied frequency analysis on referendum text descriptions to extract recurring key topics: **Foreigners**, **Military**, **Atom/Nuclear**, and **Covid**.
* **Spatial & Turnout Analysis:** Integrated geospatial visualization using **GeoPandas** alongside **Plotly** to highlight correlations between specific political topics and voter participation rates across cantons.
* **Data Cleansing & Transformation:** Processed multi-year historical datasets, handled missing values, and parsed Swiss federal statistics via `pyaxis`.

---

## Tech Stack & Libraries

* **Web Framework:** Streamlit
* **Geospatial & Data Processing:** GeoPandas, Pandas, PyAxis
* **Data Visualization:** Plotly, Seaborn, Matplotlib

---

## How to Run the Application Locally

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/](https://github.com/)[FloraGashi]/swiss-referendum-visualization.git
   cd swiss-referendum-visualization

2. **Install required dependencies:**
   ```bash
   pip install streamlit geopandas pandas matplotlib seaborn plotly pyaxis

3. **Launch the Streamlit app:**
   ```bash
   streamlit run data_visualization.py
