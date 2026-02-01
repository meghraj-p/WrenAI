import logging
from typing import Any, Dict, List, Literal, Optional, Union

import orjson
import pandas as pd
from haystack import component
from pydantic import BaseModel, Field

logger = logging.getLogger("wren-ai-service")


chart_generation_instructions = """
### INSTRUCTIONS ###

- Chart types: Bar chart, Line chart, Multi line chart, Area chart, Pie chart, Stacked bar chart, Grouped bar chart
- You can only use the chart types provided in the instructions
- Generated chart should answer the user's question and based on the semantics of the SQL query, and the sample data, sample column values are used to help you generate the suitable chart type
- If the sample data is not suitable for visualization, you must return an empty object for the schema and empty string for chart type
- If the sample data is empty, you must return an empty object for the schema and empty string for chart type
- The language for the chart and reasoning must be the same language provided by the user
- Please use the current time provided by the user to generate the chart
- For Plotly charts, you need to specify the data as traces with x and y arrays
- For multi-series charts (grouped bar, stacked bar, multi-line), create multiple trace objects
- For pie charts, use "labels" and "values" arrays instead of x/y
- For each axis and trace, generate corresponding human-readable titles/names based on the language provided by the user
- Make sure all field names used match the column names in the data

### GUIDELINES TO PLOT CHART ###

1. Understanding Your Data Types
- Nominal (Categorical): Names or labels without a specific order (e.g., types of fruits, countries).
- Ordinal: Categorical data with a meaningful order but no fixed intervals (e.g., rankings, satisfaction levels).
- Quantitative: Numerical values representing counts or measurements (e.g., sales figures, temperatures).
- Temporal: Date or time data (e.g., timestamps, dates).

2. Chart Types and When to Use Them
- Bar Chart
    - Use When: Comparing quantities across different categories.
    - Data Requirements:
        - One categorical variable (x-axis).
        - One quantitative variable (y-axis).
    - Example: Comparing sales numbers for different product categories.
- Grouped Bar Chart
    - Use When: Comparing sub-categories within main categories.
    - Data Requirements:
        - Two categorical variables (x-axis grouped by one, color-coded by another).
        - One quantitative variable (y-axis).
    - Implementation: Create multiple bar traces with barmode="group" in layout.
    - Example: Sales numbers for different products across various regions.
- Line Chart
    - Use When: Displaying trends over continuous data, especially time.
    - Data Requirements:
        - One temporal or ordinal variable (x-axis).
        - One quantitative variable (y-axis).
    - Example: Tracking monthly revenue over a year.
- Multi Line Chart
    - Use When: Displaying trends over continuous data, especially time.
    - Data Requirements:
        - One temporal or ordinal variable (x-axis).
        - Two or more quantitative variables (y-axis).
    - Implementation: Create multiple scatter traces with mode="lines+markers".
    - Example: Tracking monthly click rate and read rate over a year.
- Area Chart
    - Use When: Similar to line charts but emphasizing the volume of change over time.
    - Data Requirements:
        - Same as Line Chart.
    - Implementation: Use scatter trace with fill="tozeroy".
    - Example: Visualizing cumulative rainfall over months.
- Pie Chart
    - Use When: Showing parts of a whole as percentages.
    - Data Requirements:
        - One categorical variable.
        - One quantitative variable representing proportions.
    - Implementation: Use type="pie" with labels and values arrays.
    - Example: Market share distribution among companies.
- Stacked Bar Chart
    - Use When: Showing composition and comparison across categories.
    - Data Requirements: Same as grouped bar chart.
    - Implementation: Create multiple bar traces with barmode="stack" in layout.
    - Example: Sales by region and product type.
- Guidelines for Selecting Chart Types
    - Comparing Categories:
        - Bar Chart: Best for simple comparisons across categories.
        - Grouped Bar Chart: Use when you have sub-categories.
        - Stacked Bar Chart: Use to show composition within categories.
    - Showing Trends Over Time:
        - Line Chart: Ideal for continuous data over time.
        - Area Chart: Use when you want to emphasize volume or total value over time.
    - Displaying Proportions:
        - Pie Chart: Use for simple compositions at a single point in time.
        - Stacked Bar Chart (100%): Use for comparing compositions across multiple categories.
    
### EXAMPLES ###

1. Bar Chart
- Sample Data:
[
    {"Region": "North", "Sales": 100},
    {"Region": "South", "Sales": 200},
    {"Region": "East", "Sales": 300},
    {"Region": "West", "Sales": 400}
]
- Chart Schema:
{
    "data": [
        {
            "type": "bar",
            "x": ["North", "South", "East", "West"],
            "y": [100, 200, 300, 400],
            "name": "<NAME_IN_LANGUAGE_PROVIDED_BY_USER>",
            "marker": {"color": "#1570EF"}
        }
    ],
    "layout": {
        "title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"},
        "xaxis": {"title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"}},
        "yaxis": {"title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"}}
    }
}

2. Line Chart
- Sample Data:
[
    {"Date": "2022-01-01", "Sales": 100},
    {"Date": "2022-01-02", "Sales": 200},
    {"Date": "2022-01-03", "Sales": 300},
    {"Date": "2022-01-04", "Sales": 400}
]
- Chart Schema:
{
    "data": [
        {
            "type": "scatter",
            "mode": "lines+markers",
            "x": ["2022-01-01", "2022-01-02", "2022-01-03", "2022-01-04"],
            "y": [100, 200, 300, 400],
            "name": "<NAME_IN_LANGUAGE_PROVIDED_BY_USER>"
        }
    ],
    "layout": {
        "title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"},
        "xaxis": {"title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"}, "type": "date"},
        "yaxis": {"title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"}}
    }
}

3. Pie Chart
- Sample Data:
[
    {"Company": "Company A", "Market Share": 0.4},
    {"Company": "Company B", "Market Share": 0.3},
    {"Company": "Company C", "Market Share": 0.2},
    {"Company": "Company D", "Market Share": 0.1}
]
- Chart Schema:
{
    "data": [
        {
            "type": "pie",
            "labels": ["Company A", "Company B", "Company C", "Company D"],
            "values": [0.4, 0.3, 0.2, 0.1],
            "hole": 0
        }
    ],
    "layout": {
        "title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"}
    }
}

4. Area Chart
- Sample Data:
[
    {"Date": "2022-01-01", "Sales": 100},
    {"Date": "2022-01-02", "Sales": 200},
    {"Date": "2022-01-03", "Sales": 300},
    {"Date": "2022-01-04", "Sales": 400}
]
- Chart Schema:
{
    "data": [
        {
            "type": "scatter",
            "mode": "lines",
            "fill": "tozeroy",
            "x": ["2022-01-01", "2022-01-02", "2022-01-03", "2022-01-04"],
            "y": [100, 200, 300, 400],
            "name": "<NAME_IN_LANGUAGE_PROVIDED_BY_USER>"
        }
    ],
    "layout": {
        "title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"},
        "xaxis": {"title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"}, "type": "date"},
        "yaxis": {"title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"}}
    }
}

5. Stacked Bar Chart
- Sample Data:
[
    {"Region": "North", "Product": "A", "Sales": 100},
    {"Region": "North", "Product": "B", "Sales": 150},
    {"Region": "South", "Product": "A", "Sales": 200},
    {"Region": "South", "Product": "B", "Sales": 250},
    {"Region": "East", "Product": "A", "Sales": 300},
    {"Region": "East", "Product": "B", "Sales": 350},
    {"Region": "West", "Product": "A", "Sales": 400},
    {"Region": "West", "Product": "B", "Sales": 450}
]
- Chart Schema:
{
    "data": [
        {
            "type": "bar",
            "name": "Product A",
            "x": ["North", "South", "East", "West"],
            "y": [100, 200, 300, 400]
        },
        {
            "type": "bar",
            "name": "Product B",
            "x": ["North", "South", "East", "West"],
            "y": [150, 250, 350, 450]
        }
    ],
    "layout": {
        "title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"},
        "barmode": "stack",
        "xaxis": {"title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"}},
        "yaxis": {"title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"}}
    }
}

6. Grouped Bar Chart
- Sample Data:
[
    {"Region": "North", "Product": "A", "Sales": 100},
    {"Region": "North", "Product": "B", "Sales": 150},
    {"Region": "South", "Product": "A", "Sales": 200},
    {"Region": "South", "Product": "B", "Sales": 250},
    {"Region": "East", "Product": "A", "Sales": 300},
    {"Region": "East", "Product": "B", "Sales": 350},
    {"Region": "West", "Product": "A", "Sales": 400},
    {"Region": "West", "Product": "B", "Sales": 450}
]
- Chart Schema:
{
    "data": [
        {
            "type": "bar",
            "name": "Product A",
            "x": ["North", "South", "East", "West"],
            "y": [100, 200, 300, 400]
        },
        {
            "type": "bar",
            "name": "Product B",
            "x": ["North", "South", "East", "West"],
            "y": [150, 250, 350, 450]
        }
    ],
    "layout": {
        "title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"},
        "barmode": "group",
        "xaxis": {"title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"}},
        "yaxis": {"title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"}}
    }
}

7. Multi Line Chart
- Sample Data:
[
    {"Date": "2022-01-01", "readCount": 100, "clickCount": 10},
    {"Date": "2022-01-02", "readCount": 200, "clickCount": 30},
    {"Date": "2022-01-03", "readCount": 300, "clickCount": 20},
    {"Date": "2022-01-04", "readCount": 400, "clickCount": 40}
]
- Chart Schema:
{
    "data": [
        {
            "type": "scatter",
            "mode": "lines+markers",
            "name": "Read Count",
            "x": ["2022-01-01", "2022-01-02", "2022-01-03", "2022-01-04"],
            "y": [100, 200, 300, 400]
        },
        {
            "type": "scatter",
            "mode": "lines+markers",
            "name": "Click Count",
            "x": ["2022-01-01", "2022-01-02", "2022-01-03", "2022-01-04"],
            "y": [10, 30, 20, 40]
        }
    ],
    "layout": {
        "title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"},
        "xaxis": {"title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"}, "type": "date"},
        "yaxis": {"title": {"text": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"}}
    }
}
"""


@component
class ChartDataPreprocessor:
    @component.output_types(
        sample_data=list[dict],
        sample_column_values=dict[str, Any],
    )
    def run(
        self,
        data: Dict[str, Any],
        sample_data_count: int = 15,
        sample_column_size: int = 5,
    ):
        columns = [
            column.get("name", "") if isinstance(column, dict) else column
            for column in data.get("columns", [])
        ]
        data = data.get("data", [])

        df = pd.DataFrame(data, columns=columns)
        sample_column_values = {
            col: list(df[col].unique())[:sample_column_size] for col in df.columns
        }

        if len(df) > sample_data_count:
            sample_data = df.sample(n=sample_data_count).to_dict(orient="records")
        else:
            sample_data = df.to_dict(orient="records")

        return {
            "sample_data": sample_data,
            "sample_column_values": sample_column_values,
        }


@component
class ChartGenerationPostProcessor:
    @component.output_types(
        results=Dict[str, Any],
    )
    def run(
        self,
        replies: str,
        sample_data: list[dict],
        remove_data_from_chart_schema: Optional[bool] = True,
    ):
        try:
            generation_result = orjson.loads(replies[0])
            reasoning = generation_result.get("reasoning", "")
            chart_type = generation_result.get("chart_type", "")
            if chart_schema := generation_result.get("chart_schema", {}):
                # sometimes the chart_schema is still in string format
                if isinstance(chart_schema, str):
                    chart_schema = orjson.loads(chart_schema)

                # Validate basic Plotly structure
                if not self._validate_plotly_schema(chart_schema):
                    logger.warning("Invalid Plotly schema structure")
                    return {
                        "results": {
                            "chart_schema": {},
                            "reasoning": reasoning,
                            "chart_type": "",
                            "schema_type": "plotly",
                        }
                    }

                # Store sample data separately for frontend to inject
                chart_schema["_sample_data"] = sample_data

                if remove_data_from_chart_schema:
                    # Clear the data arrays but keep structure
                    chart_schema["_sample_data"] = []

                return {
                    "results": {
                        "chart_schema": chart_schema,
                        "reasoning": reasoning,
                        "chart_type": chart_type,
                        "schema_type": "plotly",
                    }
                }

            return {
                "results": {
                    "chart_schema": {},
                    "reasoning": reasoning,
                    "chart_type": chart_type,
                    "schema_type": "plotly",
                }
            }
        except Exception as e:
            logger.exception(f"Chart generation post-processing failed: {e}")

            return {
                "results": {
                    "chart_schema": {},
                    "reasoning": "",
                    "chart_type": "",
                    "schema_type": "plotly",
                }
            }

    def _validate_plotly_schema(self, schema: Dict[str, Any]) -> bool:
        """Basic validation for Plotly schema structure."""
        if not isinstance(schema, dict):
            return False

        # Must have data array
        if "data" not in schema or not isinstance(schema.get("data"), list):
            return False

        # Each trace must have a type
        for trace in schema.get("data", []):
            if not isinstance(trace, dict):
                return False
            if "type" not in trace:
                return False

        return True


# Plotly Pydantic Models for structured output

class PlotlyMarker(BaseModel):
    color: Optional[str] = None


class PlotlyAxisTitle(BaseModel):
    text: str


class PlotlyAxis(BaseModel):
    title: Optional[PlotlyAxisTitle] = None
    type: Optional[Literal["linear", "log", "date", "category"]] = None


class PlotlyTitle(BaseModel):
    text: str


class PlotlyLayout(BaseModel):
    title: Optional[PlotlyTitle] = None
    xaxis: Optional[PlotlyAxis] = None
    yaxis: Optional[PlotlyAxis] = None
    barmode: Optional[Literal["stack", "group", "overlay", "relative"]] = None


class PlotlyBarTrace(BaseModel):
    type: Literal["bar"] = "bar"
    x: List[Any]
    y: List[Any]
    name: Optional[str] = None
    marker: Optional[PlotlyMarker] = None


class PlotlyScatterTrace(BaseModel):
    type: Literal["scatter"] = "scatter"
    mode: Optional[Literal["lines", "markers", "lines+markers"]] = "lines+markers"
    x: List[Any]
    y: List[Any]
    name: Optional[str] = None
    fill: Optional[Literal["none", "tozeroy", "tozerox", "tonexty", "tonextx"]] = None


class PlotlyPieTrace(BaseModel):
    type: Literal["pie"] = "pie"
    labels: List[Any]
    values: List[Any]
    hole: Optional[float] = Field(default=0, ge=0, le=1)
    name: Optional[str] = None


PlotlyTrace = Union[PlotlyBarTrace, PlotlyScatterTrace, PlotlyPieTrace]


class PlotlyChartSchema(BaseModel):
    data: List[PlotlyTrace]
    layout: Optional[PlotlyLayout] = None


class ChartGenerationResults(BaseModel):
    reasoning: str
    chart_type: Literal[
        "line", "multi_line", "bar", "pie", "grouped_bar", "stacked_bar", "area", ""
    ]  # empty string for no chart
    chart_schema: PlotlyChartSchema
