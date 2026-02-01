import { cloneDeep, isNil, sortBy, uniq, isNumber } from 'lodash';
import type { Data, Layout, Config } from 'plotly.js';

// Color scheme matching the Vega theme
const colorScheme = [
  '#7763CF',
  '#444CE7',
  '#1570EF',
  '#0086C9',
  '#3E4784',
  '#E31B54',
  '#EC4A0A',
  '#EF8D0C',
  '#EBC405',
  '#5381AD',
];

// High contrast color scheme for <=5 categories
const pickedColorScheme = [
  colorScheme[4],
  colorScheme[5],
  colorScheme[8],
  colorScheme[3],
  colorScheme[0],
];

const DEFAULT_COLOR = colorScheme[2];

const COLOR = {
  GRAY_10: '#262626',
  GRAY_9: '#434343',
  GRAY_8: '#65676c',
  GRAY_5: '#d9d9d9',
};

export interface PlotlySpec {
  data: Data[];
  layout?: Partial<Layout>;
  _sample_data?: Record<string, any>[];
}

export interface PlotlyChartOptions {
  width?: number | string;
  height?: number | string;
  categoriesLimit?: number;
  isShowTopCategories?: boolean;
  isHideLegend?: boolean;
  isHideTitle?: boolean;
  donutInner?: number | false;
}

export default class PlotlySpecHandler {
  public data: Data[];
  public layout: Partial<Layout>;
  public config: Partial<Config>;
  public options: PlotlyChartOptions;
  private values: Record<string, any>[];

  constructor(
    spec: PlotlySpec,
    values: Record<string, any>[],
    options?: PlotlyChartOptions
  ) {
    this.values = values || [];

    // Default options
    this.options = {
      width: isNil(options?.width) ? undefined : options.width,
      height: isNil(options?.height) ? undefined : options.height,
      categoriesLimit: isNil(options?.categoriesLimit)
        ? 25
        : options.categoriesLimit,
      isShowTopCategories: isNil(options?.isShowTopCategories)
        ? false
        : options.isShowTopCategories,
      isHideLegend: isNil(options?.isHideLegend) ? false : options.isHideLegend,
      isHideTitle: isNil(options?.isHideTitle) ? false : options.isHideTitle,
      donutInner: isNil(options?.donutInner) ? 0.3 : options.donutInner,
    };

    // Clone spec to avoid mutations
    const clonedSpec = cloneDeep(spec);

    // Initialize data and layout
    this.data = clonedSpec.data || [];
    this.layout = this.initLayout(clonedSpec.layout);

    // Default config
    this.config = {
      displayModeBar: true,
      modeBarButtonsToRemove: ['lasso2d', 'select2d'],
      displaylogo: false,
      responsive: true,
    };

    // Process the spec
    this.parseSpec();
  }

  private initLayout(layout?: Partial<Layout>): Partial<Layout> {
    return {
      ...layout,
      colorway: colorScheme,
      font: {
        family: 'Roboto, Arial, Noto Sans, sans-serif',
        color: COLOR.GRAY_10,
      },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      margin: { t: 50, b: 50, l: 50, r: 20 },
      autosize: true,
      showlegend: !this.options.isHideLegend,
      legend: {
        font: { size: 10, color: COLOR.GRAY_8 },
      },
      xaxis: {
        ...layout?.xaxis,
        gridcolor: COLOR.GRAY_5,
        tickfont: { size: 10, color: COLOR.GRAY_8 },
        titlefont: { size: 12, color: COLOR.GRAY_9 },
        tickangle: -45,
      },
      yaxis: {
        ...layout?.yaxis,
        gridcolor: COLOR.GRAY_5,
        tickfont: { size: 10, color: COLOR.GRAY_8 },
        titlefont: { size: 12, color: COLOR.GRAY_9 },
      },
    };
  }

  private parseSpec() {
    // Inject data values into traces
    this.injectDataValues();

    // Filter top categories if needed
    if (this.options.isShowTopCategories) {
      this.filterTopCategories();
    }

    // Apply color scheme based on number of categories
    this.applyColorScheme();

    // Apply donut inner radius for pie charts
    this.applyDonutStyle();

    // Hide title if needed
    if (this.options.isHideTitle) {
      delete this.layout.title;
    }
  }

  private injectDataValues() {
    if (!this.values || this.values.length === 0) return;

    // Try to inject data into traces based on field references
    this.data = this.data.map((trace) => {
      const updatedTrace = { ...trace };

      // Handle different trace types
      if (trace.type === 'pie') {
        // For pie charts, use labels and values
        if (this.isPieFieldReference(trace)) {
          const labelField = this.extractFieldName((trace as any).labels);
          const valueField = this.extractFieldName((trace as any).values);

          if (labelField && valueField) {
            (updatedTrace as any).labels = this.values.map(
              (v) => v[labelField]
            );
            (updatedTrace as any).values = this.values.map(
              (v) => v[valueField]
            );
          }
        }
      } else {
        // For bar/scatter charts, use x and y
        if (this.isFieldReference(trace)) {
          const xField = this.extractFieldName((trace as any).x);
          const yField = this.extractFieldName((trace as any).y);

          if (xField) {
            (updatedTrace as any).x = this.values.map((v) => v[xField]);
          }
          if (yField) {
            (updatedTrace as any).y = this.values.map((v) => v[yField]);
          }
        }
      }

      return updatedTrace;
    });
  }

  private isPieFieldReference(trace: Data): boolean {
    const labels = (trace as any).labels;
    const values = (trace as any).values;
    return (
      (typeof labels === 'string' || (Array.isArray(labels) && labels.length === 0)) &&
      (typeof values === 'string' || (Array.isArray(values) && values.length === 0))
    );
  }

  private isFieldReference(trace: Data): boolean {
    const x = (trace as any).x;
    const y = (trace as any).y;
    return (
      (typeof x === 'string' || (Array.isArray(x) && x.length === 0)) &&
      (typeof y === 'string' || (Array.isArray(y) && y.length === 0))
    );
  }

  private extractFieldName(value: any): string | null {
    if (typeof value === 'string') {
      return value;
    }
    return null;
  }

  private filterTopCategories() {
    const limit = this.options.categoriesLimit || 25;

    this.data = this.data.map((trace) => {
      if (trace.type === 'pie') {
        const labels = (trace as any).labels as any[];
        const values = (trace as any).values as number[];

        if (labels && values && labels.length > limit) {
          // Sort by values descending and take top N
          const paired = labels.map((label, i) => ({ label, value: values[i] }));
          const sorted = sortBy(paired, (p) => -p.value).slice(0, limit);

          return {
            ...trace,
            labels: sorted.map((p) => p.label),
            values: sorted.map((p) => p.value),
          };
        }
      } else {
        const x = (trace as any).x as any[];
        const y = (trace as any).y as any[];

        if (x && y && x.length > limit) {
          // For bar/line charts, take first N items (assuming sorted by importance)
          const uniqueX = uniq(x);
          if (uniqueX.length > limit) {
            const topX = uniqueX.slice(0, limit);
            const indices = x
              .map((val, i) => (topX.includes(val) ? i : -1))
              .filter((i) => i !== -1);

            return {
              ...trace,
              x: indices.map((i) => x[i]),
              y: indices.map((i) => y[i]),
            };
          }
        }
      }
      return trace;
    });
  }

  private applyColorScheme() {
    // Count unique categories across all traces
    let categories: any[] = [];

    this.data.forEach((trace) => {
      if (trace.type === 'pie') {
        const labels = (trace as any).labels as any[];
        if (labels) {
          categories = categories.concat(labels);
        }
      } else {
        // For bar/scatter, the trace name or x values represent categories
        const x = (trace as any).x as any[];
        if (x) {
          categories = categories.concat(x);
        }
      }
    });

    const uniqueCategories = uniq(categories);

    // Use high contrast colors for <=5 categories
    if (uniqueCategories.length <= 5) {
      this.layout.colorway = pickedColorScheme;
    }

    // Apply default color to single traces without colors
    this.data = this.data.map((trace, index) => {
      if (trace.type === 'bar' || trace.type === 'scatter') {
        if (!(trace as any).marker?.color && this.data.length === 1) {
          return {
            ...trace,
            marker: {
              ...(trace as any).marker,
              color: DEFAULT_COLOR,
            },
          };
        }
      }
      return trace;
    });
  }

  private applyDonutStyle() {
    if (this.options.donutInner === false) return;

    this.data = this.data.map((trace) => {
      if (trace.type === 'pie') {
        return {
          ...trace,
          hole: this.options.donutInner || 0.3,
        };
      }
      return trace;
    });
  }

  public getChartSpec(): { data: Data[]; layout: Partial<Layout>; config: Partial<Config> } | null {
    // Check if we have too many categories
    const categories = this.getAllCategories();
    if (categories.length > (this.options.categoriesLimit || 25)) {
      return null;
    }

    return {
      data: this.data,
      layout: this.layout,
      config: this.config,
    };
  }

  private getAllCategories(): any[] {
    let categories: any[] = [];

    this.data.forEach((trace) => {
      if (trace.type === 'pie') {
        const labels = (trace as any).labels as any[];
        if (labels) {
          categories = categories.concat(labels);
        }
      } else {
        const x = (trace as any).x as any[];
        if (x) {
          categories = categories.concat(x);
        }
      }
    });

    return uniq(categories);
  }
}

/**
 * Detect if a chart schema is Plotly or Vega-Lite format
 */
export function detectSchemaType(schema: any): 'plotly' | 'vega-lite' {
  if (!schema || typeof schema !== 'object') {
    return 'vega-lite';
  }

  // Plotly schemas have 'data' array with traces
  if (Array.isArray(schema.data) && schema.data.length > 0) {
    const firstTrace = schema.data[0];
    // Plotly traces have 'type' like 'bar', 'scatter', 'pie'
    if (firstTrace && typeof firstTrace.type === 'string') {
      return 'plotly';
    }
  }

  // Vega-Lite schemas have 'mark' and 'encoding'
  if (schema.mark || schema.encoding || schema.$schema?.includes('vega')) {
    return 'vega-lite';
  }

  // Default to vega-lite for backward compatibility
  return 'vega-lite';
}
