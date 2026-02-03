import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import clsx from 'clsx';
import { Alert, Button, Tooltip } from 'antd';
import PlotlySpecHandler, { PlotlySpec } from './plotlyHandler';
import ReloadOutlined from '@ant-design/icons/ReloadOutlined';
import EditOutlined from '@ant-design/icons/EditOutlined';
import EyeOutlined from '@ant-design/icons/EyeOutlined';
import PushPinOutlined from '@ant-design/icons/PushpinOutlined';
import ErrorCollapse from '@/components/ErrorCollapse';

// Dynamically import Plotly to avoid SSR issues
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface ChartProps {
  className?: string;
  width?: number | string;
  height?: number | string;
  spec?: PlotlySpec;
  schemaType?: 'plotly';
  values?: Record<string, any>[];
  autoFilter?: boolean;
  hideActions?: boolean;
  hideTitle?: boolean;
  hideLegend?: boolean;
  forceUpdate?: number;
  isPinned?: boolean;
  onReload?: () => void;
  onEdit?: () => void;
  onPin?: () => void;
}

export default function Chart(props: ChartProps) {
  const {
    className,
    spec,
    values,
    width = 600,
    height = 320,
    autoFilter,
    hideActions,
    hideTitle,
    hideLegend,
    forceUpdate,
    isPinned,
    onReload,
    onEdit,
    onPin,
  } = props;

  const [donutInner, setDonutInner] = useState(0.3);
  const [parsedError, setParsedError] = useState<Record<string, any>>(null);
  const [isShowTopCategories, setIsShowTopCategories] = useState(false);

  // Plotly state
  const [plotlySpec, setPlotlySpec] = useState<{
    data: any[];
    layout: any;
    config: any;
  } | null>(null);

  // Parse Plotly spec
  useEffect(() => {
    if (!spec || !values) return;
    try {
      const specHandler = new PlotlySpecHandler(spec as PlotlySpec, values, {
        categoriesLimit: 25,
        isShowTopCategories: autoFilter || isShowTopCategories,
        isHideLegend: hideLegend,
        isHideTitle: hideTitle,
        donutInner: donutInner || 0.3,
      });
      const chartSpec = specHandler.getChartSpec();
      setPlotlySpec(chartSpec);
      setParsedError(null);
    } catch (error) {
      console.error(error);
      setParsedError({
        code: 'CLIENT_PARSE_ERROR',
        shortMessage: 'Failed to render chart visualization',
        message: error?.message,
        stacktrace: error?.stack?.split('\n') || [],
      });
    }
    return () => {
      setPlotlySpec(null);
      setParsedError(null);
    };
  }, [
    spec,
    values,
    isShowTopCategories,
    donutInner,
    forceUpdate,
    autoFilter,
    hideLegend,
    hideTitle,
  ]);

  useEffect(() => {
    // Set donut inner radius based on height
    if (typeof height === 'number') {
      setDonutInner(height * 0.15 / 100);
    }
  }, [forceUpdate, height]);

  const onShowTopCategories = () => {
    setIsShowTopCategories(!isShowTopCategories);
  };

  const getChartContent = () => {
    if (!values || values.length === 0) return <div>No available data</div>;

    if (parsedError) {
      return (
        <div
          className={clsx({ 'mx-4 mt-12': !isPinned })}
          onMouseDown={(e) => e.stopPropagation()}
        >
          <Alert
            showIcon
            type="error"
            message={parsedError.shortMessage}
            description={
              <ErrorCollapse message={parsedError.message} defaultActive />
            }
          />
        </div>
      );
    }

    if (plotlySpec === null) {
      return (
        <Alert
          className="mt-12 mb-4 mx-4"
          message={
            <div className="d-flex align-center justify-space-between">
              <div>
                There are too many categories to display effectively. Click
                'Show top 25' to view the top results, or ask a follow-up
                question to focus on a specific group or filter results.
              </div>
              <Button
                size="small"
                icon={<EyeOutlined />}
                onClick={onShowTopCategories}
              >
                Show top 25
              </Button>
            </div>
          }
          type="warning"
        />
      );
    }

    return (
      <Plot
        data={plotlySpec.data}
        layout={{
          ...plotlySpec.layout,
          width: typeof width === 'number' ? width : undefined,
          height: typeof height === 'number' ? height : undefined,
          autosize: true,
        }}
        config={plotlySpec.config}
        style={{ width, height }}
        useResizeHandler
      />
    );
  };

  const isAdditionalShow = !!onReload || !!onEdit || !!onPin;

  return (
    <div
      className={clsx(
        'adm-chart',
        { 'adm-chart--no-actions': hideActions },
        className,
      )}
      style={{ width }}
    >
      {isAdditionalShow && (
        <div className="adm-chart-additional d-flex justify-content-between align-center">
          {!!onReload && (
            <Tooltip title="Regenerate chart">
              <button onClick={onReload}>
                <ReloadOutlined />
              </button>
            </Tooltip>
          )}
          {!!onEdit && (
            <Tooltip title="Edit chart">
              <button onClick={onEdit}>
                <EditOutlined />
              </button>
            </Tooltip>
          )}
          {!!onPin && (
            <Tooltip title="Pin chart to dashboard">
              <button onClick={onPin}>
                <PushPinOutlined />
              </button>
            </Tooltip>
          )}
        </div>
      )}
      {getChartContent()}
    </div>
  );
}
