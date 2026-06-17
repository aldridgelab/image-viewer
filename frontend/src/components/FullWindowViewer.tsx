import type { CSSProperties, PointerEvent as ReactPointerEvent, WheelEvent as ReactWheelEvent } from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  ChevronLeft,
  ChevronRight,
  Contrast,
  Download,
  Maximize2,
  SlidersHorizontal,
  Star,
  SunMedium,
  X,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import { getViewerCompositeUrl, getViewerImageUrl } from '../api/client';
import type { ViewerCompositeChannels, ViewerItem, ViewerRenderMode } from '../api/types';

interface FullWindowViewerProps {
  item: ViewerItem;
  items: ViewerItem[];
  channelNames: string[];
  initialChannel: number;
  cacheKey: number;
  renderMode: ViewerRenderMode;
  compositeChannels: ViewerCompositeChannels;
  onClose: () => void;
  onSelectItem: (item: ViewerItem) => void;
  onFavoriteToggle: (item: ViewerItem) => void;
}

interface Point {
  x: number;
  y: number;
}

interface ChannelAdjustment {
  brightness: number;
  contrast: number;
  normalize: boolean;
}

const MIN_ZOOM = 1;
const MAX_ZOOM = 8;
const ZOOM_STEP = 1.2;

const DEFAULT_CHANNEL_ADJUSTMENT: ChannelAdjustment = {
  brightness: 100,
  contrast: 100,
  normalize: false,
};

function clampChannel(channel: number, totalChannels: number): number {
  if (totalChannels <= 0) {
    return 0;
  }
  return Math.min(Math.max(channel, 0), totalChannels - 1);
}

function clampValue(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function clampZoom(value: number): number {
  return clampValue(value, MIN_ZOOM, MAX_ZOOM);
}

function getImageFilter(adjustment: ChannelAdjustment): string {
  return `brightness(${adjustment.brightness}%) contrast(${adjustment.contrast}%)`;
}

function formatBytes(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return 'Unknown';
  }
  if (value < 1024) {
    return `${value} B`;
  }
  const units = ['KB', 'MB', 'GB'];
  let scaled = value / 1024;
  for (const unit of units) {
    if (scaled < 1024 || unit === units[units.length - 1]) {
      return `${scaled.toFixed(scaled >= 100 ? 0 : 1)} ${unit}`;
    }
    scaled /= 1024;
  }
  return `${value} B`;
}

function formatModifiedTime(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return 'Unknown';
  }
  return new Date(value * 1000).toLocaleString();
}

function downloadUrl(url: string, filename: string): void {
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

function isEditableTarget(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLSelectElement
  );
}

export function FullWindowViewer({
  item,
  items,
  channelNames,
  initialChannel,
  cacheKey,
  renderMode,
  compositeChannels,
  onClose,
  onSelectItem,
  onFavoriteToggle,
}: FullWindowViewerProps) {
  const [channel, setChannel] = useState(() => clampChannel(initialChannel, item.n_channels));
  const [zoom, setZoom] = useState(MIN_ZOOM);
  const [pan, setPan] = useState<Point>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [channelAdjustments, setChannelAdjustments] = useState<Record<number, ChannelAdjustment>>(
    {},
  );
  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    origin: Point;
  } | null>(null);
  const itemIndex = useMemo(
    () => items.findIndex((candidate) => candidate.id === item.id),
    [item.id, items],
  );
  const channelCount = Math.max(1, item.n_channels);
  const activeChannelName =
    renderMode === 'composite' ? 'RGB composite' : channelNames[channel] || `Channel ${channel + 1}`;
  const activeAdjustment = channelAdjustments[channel] ?? DEFAULT_CHANNEL_ADJUSTMENT;
  const activeImageUrl =
    renderMode === 'composite'
      ? getViewerCompositeUrl(item.id, {
          channels: compositeChannels,
          channelCount,
          normalize: activeAdjustment.normalize,
          cacheKey,
        })
      : getViewerImageUrl(item.id, channel, {
          normalize: activeAdjustment.normalize,
          cacheKey,
        });
  const activeImageStyle: CSSProperties = {
    filter: getImageFilter(activeAdjustment),
    transform: `translate3d(${pan.x}px, ${pan.y}px, 0) scale(${zoom})`,
  };
  const canZoomIn = zoom < MAX_ZOOM;
  const canZoomOut = zoom > MIN_ZOOM;
  const hasPreviousItem = itemIndex > 0;
  const hasNextItem = itemIndex >= 0 && itemIndex < items.length - 1;
  const exportFilename = `${item.id}-${renderMode === 'composite' ? 'rgb-composite' : `channel-${channel + 1}`}.png`;

  const shiftChannel = useCallback((delta: number) => {
    setChannel((current) => (current + delta + channelCount) % channelCount);
  }, [channelCount]);

  const shiftItem = useCallback((delta: number) => {
    if (itemIndex < 0) {
      return;
    }
    const nextIndex = itemIndex + delta;
    if (nextIndex >= 0 && nextIndex < items.length) {
      onSelectItem(items[nextIndex]);
    }
  }, [itemIndex, items, onSelectItem]);

  const resetToFit = useCallback(() => {
    dragRef.current = null;
    setIsPanning(false);
    setZoom(MIN_ZOOM);
    setPan({ x: 0, y: 0 });
  }, []);

  const changeZoom = useCallback((factor: number) => {
    const nextZoom = clampZoom(zoom * factor);
    setZoom(nextZoom);
    if (nextZoom <= MIN_ZOOM) {
      dragRef.current = null;
      setIsPanning(false);
      setPan({ x: 0, y: 0 });
    }
  }, [zoom]);

  const updateActiveAdjustment = useCallback(
    (patch: Partial<ChannelAdjustment>) => {
      setChannelAdjustments((current) => ({
        ...current,
        [channel]: {
          ...DEFAULT_CHANNEL_ADJUSTMENT,
          ...current[channel],
          ...patch,
        },
      }));
    },
    [channel],
  );

  const toggleActiveNormalize = useCallback(() => {
    setChannelAdjustments((current) => {
      const currentAdjustment = {
        ...DEFAULT_CHANNEL_ADJUSTMENT,
        ...current[channel],
      };
      return {
        ...current,
        [channel]: {
          ...currentAdjustment,
          normalize: !currentAdjustment.normalize,
        },
      };
    });
  }, [channel]);

  const handleExportCurrent = useCallback(() => {
    downloadUrl(activeImageUrl, exportFilename);
  }, [activeImageUrl, exportFilename]);

  const handleStageWheel = useCallback(
    (event: ReactWheelEvent<HTMLDivElement>) => {
      event.preventDefault();
      changeZoom(event.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP);
    },
    [changeZoom],
  );

  const handleStagePointerDown = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (zoom <= MIN_ZOOM || event.button !== 0) {
        return;
      }
      event.preventDefault();
      dragRef.current = {
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        origin: pan,
      };
      setIsPanning(true);
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    [pan, zoom],
  );

  const handleStagePointerMove = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) {
      return;
    }
    event.preventDefault();
    setPan({
      x: drag.origin.x + event.clientX - drag.startX,
      y: drag.origin.y + event.clientY - drag.startY,
    });
  }, []);

  const endStagePan = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) {
      return;
    }
    dragRef.current = null;
    setIsPanning(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }, []);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (isEditableTarget(event.target)) {
        return;
      }
      if (event.metaKey || event.ctrlKey || event.altKey) {
        return;
      }
      if (event.key === 'Escape') {
        onClose();
      } else if (event.key === 'ArrowLeft') {
        event.preventDefault();
        shiftChannel(-1);
      } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        shiftChannel(1);
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        shiftItem(-1);
      } else if (event.key === 'ArrowDown') {
        event.preventDefault();
        shiftItem(1);
      } else if (event.key === '+' || event.key === '=') {
        event.preventDefault();
        changeZoom(ZOOM_STEP);
      } else if (event.key === '-' || event.key === '_') {
        event.preventDefault();
        changeZoom(1 / ZOOM_STEP);
      } else if (event.key === '0') {
        event.preventDefault();
        resetToFit();
      } else if (event.key.toLowerCase() === 'n') {
        event.preventDefault();
        toggleActiveNormalize();
      } else if (event.key.toLowerCase() === 'f') {
        event.preventDefault();
        onFavoriteToggle(item);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    changeZoom,
    item,
    onClose,
    onFavoriteToggle,
    resetToFit,
    shiftChannel,
    shiftItem,
    toggleActiveNormalize,
  ]);

  return (
    <section className="detail-shell" aria-label="Selected image">
      <div className="detail-toolbar">
        <div className="detail-toolbar__left">
          <button
            className="icon-button"
            type="button"
            onClick={onClose}
            title="Close (Esc)"
            aria-label="Close"
          >
            <X size={18} />
          </button>
          <div className="detail-title">
            <span>{item.filename}</span>
            <small>
              {activeChannelName} · {item.shape.length ? item.shape.join(' x ') : 'unknown shape'}
            </small>
          </div>
        </div>

        <div className="detail-toolbar__controls">
          <button
            className="icon-button"
            type="button"
            onClick={() => shiftItem(-1)}
            disabled={!hasPreviousItem}
            title="Previous image (Arrow Up)"
            aria-label="Previous image"
          >
            <ArrowUp size={18} />
          </button>
          <button
            className="icon-button"
            type="button"
            onClick={() => shiftItem(1)}
            disabled={!hasNextItem}
            title="Next image (Arrow Down)"
            aria-label="Next image"
          >
            <ArrowDown size={18} />
          </button>
          <button
            className="icon-button"
            type="button"
            onClick={() => shiftChannel(-1)}
            title="Previous channel (Arrow Left)"
            aria-label="Previous channel"
          >
            <ArrowLeft size={18} />
          </button>
          <button
            className="icon-button"
            type="button"
            onClick={() => shiftChannel(1)}
            title="Next channel (Arrow Right)"
            aria-label="Next channel"
          >
            <ArrowRight size={18} />
          </button>
          <span className="toolbar-divider" aria-hidden="true" />
          <button
            className="icon-button"
            type="button"
            onClick={handleExportCurrent}
            title="Export current view"
            aria-label="Export current view"
          >
            <Download size={18} />
          </button>
          <span className="toolbar-divider" aria-hidden="true" />
          <button
            className="icon-button"
            type="button"
            onClick={() => changeZoom(1 / ZOOM_STEP)}
            disabled={!canZoomOut}
            title="Zoom out (-)"
            aria-label="Zoom out"
          >
            <ZoomOut size={18} />
          </button>
          <span className="zoom-readout" title="Current zoom">
            {Math.round(zoom * 100)}%
          </span>
          <button
            className="icon-button"
            type="button"
            onClick={() => changeZoom(ZOOM_STEP)}
            disabled={!canZoomIn}
            title="Zoom in (+)"
            aria-label="Zoom in"
          >
            <ZoomIn size={18} />
          </button>
          <button
            className="icon-button"
            type="button"
            onClick={resetToFit}
            disabled={zoom === MIN_ZOOM && pan.x === 0 && pan.y === 0}
            title="Reset to fit (0)"
            aria-label="Reset to fit"
          >
            <Maximize2 size={18} />
          </button>
          <span className="toolbar-divider" aria-hidden="true" />
          <button
            className={`icon-button ${item.is_favorite ? 'is-active' : ''}`}
            type="button"
            onClick={() => onFavoriteToggle(item)}
            title={item.is_favorite ? 'Remove favorite (F)' : 'Add favorite (F)'}
            aria-label={item.is_favorite ? 'Remove favorite' : 'Add favorite'}
            aria-pressed={item.is_favorite}
          >
            <Star size={18} fill={item.is_favorite ? 'currentColor' : 'none'} />
          </button>
        </div>
      </div>

      <div className="detail-body">
        <button
          className="stage-nav stage-nav--left"
          type="button"
          onClick={() => shiftChannel(-1)}
          title="Previous channel (Arrow Left)"
          aria-label="Previous channel"
        >
          <ChevronLeft size={24} />
        </button>
        <div
          className={`stage ${zoom > MIN_ZOOM ? 'is-zoomed' : ''} ${isPanning ? 'is-panning' : ''}`}
          onWheel={handleStageWheel}
          onPointerDown={handleStagePointerDown}
          onPointerMove={handleStagePointerMove}
          onPointerUp={endStagePan}
          onPointerCancel={endStagePan}
          onPointerLeave={endStagePan}
        >
          <img
            src={activeImageUrl}
            alt={`${item.filename} ${activeChannelName}`}
            draggable={false}
            style={activeImageStyle}
          />
        </div>
        <button
          className="stage-nav stage-nav--right"
          type="button"
          onClick={() => shiftChannel(1)}
          title="Next channel (Arrow Right)"
          aria-label="Next channel"
        >
          <ChevronRight size={24} />
        </button>

        <aside className="detail-sidepanel" aria-label="Channel controls">
          <div className="image-controls">
            <label className="image-control">
              <span>
                <SunMedium size={14} />
                Brightness
              </span>
              <input
                type="range"
                min="0"
                max="200"
                value={activeAdjustment.brightness}
                onChange={(event) =>
                  updateActiveAdjustment({ brightness: Number(event.currentTarget.value) })
                }
                title={`Brightness for ${activeChannelName}`}
                aria-label={`Brightness for ${activeChannelName}`}
              />
              <output>{activeAdjustment.brightness}%</output>
            </label>
            <label className="image-control">
              <span>
                <Contrast size={14} />
                Contrast
              </span>
              <input
                type="range"
                min="0"
                max="200"
                value={activeAdjustment.contrast}
                onChange={(event) =>
                  updateActiveAdjustment({ contrast: Number(event.currentTarget.value) })
                }
                title={`Contrast for ${activeChannelName}`}
                aria-label={`Contrast for ${activeChannelName}`}
              />
              <output>{activeAdjustment.contrast}%</output>
            </label>
            <label
              className={`normalize-toggle ${activeAdjustment.normalize ? 'is-active' : ''}`}
              title={`Normalize ${activeChannelName} (N)`}
            >
              <span>
                <SlidersHorizontal size={14} />
                Normalize
              </span>
              <input
                type="checkbox"
                checked={activeAdjustment.normalize}
                onChange={toggleActiveNormalize}
                aria-label={`Normalize ${activeChannelName}`}
              />
            </label>
          </div>

          <div className="channel-rail" aria-label="Channels">
            {Array.from({ length: channelCount }).map((_, index) => {
              const adjustment = channelAdjustments[index] ?? DEFAULT_CHANNEL_ADJUSTMENT;
              const channelName = channelNames[index] || `Channel ${index + 1}`;
              return (
                <button
                  type="button"
                  className={`channel-thumb ${index === channel ? 'is-selected' : ''}`}
                  key={index}
                  onClick={() => setChannel(index)}
                  title={channelName}
                >
                  <img
                    src={getViewerImageUrl(item.id, index, {
                      normalize: adjustment.normalize,
                      cacheKey,
                    })}
                    alt={channelName}
                    draggable={false}
                    style={{ filter: getImageFilter(adjustment) }}
                  />
                  <span>{channelNames[index] || `Ch ${index + 1}`}</span>
                </button>
              );
            })}
          </div>

          <dl className="metadata-panel" aria-label="Image metadata">
            <div>
              <dt>File</dt>
              <dd title={item.filename}>{item.filename}</dd>
            </div>
            <div>
              <dt>Path</dt>
              <dd title={item.source_path}>{item.source_path}</dd>
            </div>
            <div>
              <dt>Shape</dt>
              <dd>{item.shape.length ? item.shape.join(' x ') : 'Unknown'}</dd>
            </div>
            <div>
              <dt>Axes</dt>
              <dd>{item.axes || 'Unknown'}</dd>
            </div>
            <div>
              <dt>Dtype</dt>
              <dd>{item.dtype || 'Unknown'}</dd>
            </div>
            <div>
              <dt>Size</dt>
              <dd>{formatBytes(item.file_size_bytes)}</dd>
            </div>
            <div>
              <dt>Modified</dt>
              <dd>{formatModifiedTime(item.modified_time)}</dd>
            </div>
            <div>
              <dt>Channels</dt>
              <dd>{channelNames.slice(0, channelCount).join(', ') || `${channelCount}`}</dd>
            </div>
          </dl>
        </aside>
      </div>
    </section>
  );
}
