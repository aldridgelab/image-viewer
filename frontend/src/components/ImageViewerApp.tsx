import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ChevronDown,
  FolderOpen,
  Loader2,
  RefreshCw,
  Settings,
  XCircle,
} from 'lucide-react';
import {
  clearViewerConfig,
  exportViewerContactSheet,
  getViewerConfig,
  getViewerItems,
  inspectViewerDir,
  refreshViewerFiles,
  setViewerConfig,
  toggleViewerFavorite,
} from '../api/client';
import type {
  ViewerChannelColor,
  ViewerCompositeChannels,
  ViewerConfig,
  ViewerInspectResponse,
  ViewerItem,
  ViewerRenderMode,
} from '../api/types';
import { BrowserToolbar } from './BrowserToolbar';
import { EmptyState } from './EmptyState';
import { FullWindowViewer } from './FullWindowViewer';
import { GridItem } from './GridItem';
import { SetupPanel } from './SetupPanel';
import { ZoomPopup } from './ZoomPopup';
import { APP_VERSION } from '../version';

function clampChannel(channel: number, totalChannels: number): number {
  if (totalChannels <= 0) {
    return 0;
  }
  return Math.min(Math.max(channel, 0), totalChannels - 1);
}

function detectedNamesFor(result: ViewerInspectResponse): string[] {
  return result.detected_channel_names.length > 0
    ? result.detected_channel_names
    : result.default_channel_names;
}

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function ImageViewerApp() {
  const [config, setConfig] = useState<ViewerConfig | null>(null);
  const [isConfigured, setIsConfigured] = useState(false);
  const [showSetup, setShowSetup] = useState(false);

  const [directory, setDirectory] = useState('');
  const [pattern, setPattern] = useState('*.tif');
  const [channelNames, setChannelNames] = useState<string[]>([]);
  const [defaultChannel, setDefaultChannel] = useState(0);
  const [inspectResult, setInspectResult] = useState<ViewerInspectResponse | null>(null);
  const [isInspecting, setIsInspecting] = useState(false);
  const [isApplying, setIsApplying] = useState(false);

  const [items, setItems] = useState<ViewerItem[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [limit, setLimit] = useState(120);
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  const [renderMode, setRenderMode] = useState<ViewerRenderMode>('single');
  const [compositeChannels, setCompositeChannels] = useState<ViewerCompositeChannels>({
    red: 0,
    green: 1,
    blue: 2,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cacheKey, setCacheKey] = useState(0);

  const [hoveredItem, setHoveredItem] = useState<ViewerItem | null>(null);
  const [hoverPosition, setHoverPosition] = useState({ x: 0, y: 0 });
  const [isZKeyPressed, setIsZKeyPressed] = useState(false);
  const [selectedItem, setSelectedItem] = useState<ViewerItem | null>(null);
  const hoverTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    getViewerConfig()
      .then((viewerConfig) => {
        setConfig(viewerConfig);
        if (viewerConfig.viewer_dir) {
          setIsConfigured(true);
          setDirectory(viewerConfig.viewer_dir);
          setPattern(viewerConfig.viewer_pattern);
          setChannelNames(viewerConfig.viewer_channel_names);
          setDefaultChannel(
            clampChannel(
              viewerConfig.viewer_default_channel,
              viewerConfig.viewer_channel_names.length,
            ),
          );
        } else {
          setShowSetup(true);
        }
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Failed to load viewer configuration');
        setShowSetup(true);
      });
  }, []);

  const loadItems = useCallback(async () => {
    if (!isConfigured) {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const response = await getViewerItems({
        search: search.trim() || undefined,
        limit,
        favorites_only: favoritesOnly,
      });
      setItems(response.items);
      setTotal(response.total);
      setSelectedItem((current) => {
        if (!current) {
          return null;
        }
        return response.items.find((item) => item.id === current.id) ?? current;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load TIFF files');
    } finally {
      setIsLoading(false);
    }
  }, [favoritesOnly, isConfigured, limit, search]);

  useEffect(() => {
    if (!isConfigured) {
      return undefined;
    }
    const timer = window.setTimeout(() => {
      void loadItems();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [isConfigured, loadItems]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'z' || event.key === 'Z') {
        setIsZKeyPressed(true);
      }
    };
    const handleKeyUp = (event: KeyboardEvent) => {
      if (event.key === 'z' || event.key === 'Z') {
        setIsZKeyPressed(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);

  const handleInspect = useCallback(async () => {
    if (!directory.trim()) {
      setError('Enter a directory path first.');
      return;
    }
    setIsInspecting(true);
    setError(null);
    setInspectResult(null);
    try {
      const result = await inspectViewerDir({
        directory: directory.trim(),
        pattern: pattern.trim() || '*.tif',
      });
      setInspectResult(result);
      const names = detectedNamesFor(result);
      setChannelNames(names);
      setDefaultChannel((current) => clampChannel(current, names.length));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to inspect directory');
    } finally {
      setIsInspecting(false);
    }
  }, [directory, pattern]);

  const handleApply = useCallback(async () => {
    if (!inspectResult || inspectResult.total_images === 0) {
      setError('Inspect a directory with TIFF files before applying.');
      return;
    }
    if (channelNames.some((name) => !name.trim())) {
      setError('Every detected channel needs a name.');
      return;
    }

    setIsApplying(true);
    setError(null);
    try {
      const viewerConfig = await setViewerConfig({
        viewer_dir: directory.trim(),
        viewer_pattern: pattern.trim() || '*.tif',
        viewer_channel_names: channelNames,
        viewer_default_channel: clampChannel(defaultChannel, channelNames.length),
      });
      setConfig(viewerConfig);
      setChannelNames(viewerConfig.viewer_channel_names);
      setDefaultChannel(
        clampChannel(viewerConfig.viewer_default_channel, viewerConfig.viewer_channel_names.length),
      );
      setIsConfigured(true);
      setShowSetup(false);
      setCacheKey((current) => current + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply viewer configuration');
    } finally {
      setIsApplying(false);
    }
  }, [channelNames, defaultChannel, directory, inspectResult, pattern]);

  const handleRefresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      await refreshViewerFiles();
      setCacheKey((current) => current + 1);
      await loadItems();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh file list');
    } finally {
      setIsLoading(false);
    }
  }, [loadItems]);

  const handleClear = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const viewerConfig = await clearViewerConfig();
      setConfig(viewerConfig);
      setIsConfigured(false);
      setShowSetup(true);
      setItems([]);
      setTotal(0);
      setSearch('');
      setLimit(120);
      setFavoritesOnly(false);
      setRenderMode('single');
      setCompositeChannels({ red: 0, green: 1, blue: 2 });
      setInspectResult(null);
      setChannelNames([]);
      setDefaultChannel(0);
      setDirectory('');
      setPattern('*.tif');
      setSelectedItem(null);
      setCacheKey((current) => current + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear viewer configuration');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleFavoriteToggle = useCallback(async (item: ViewerItem) => {
    try {
      const response = await toggleViewerFavorite(item.id, !item.is_favorite);
      setItems((current) =>
        current.map((candidate) =>
          candidate.id === item.id
            ? { ...candidate, is_favorite: response.is_favorite }
            : candidate,
        ),
      );
      setSelectedItem((current) =>
        current?.id === item.id ? { ...current, is_favorite: response.is_favorite } : current,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update favorite');
    }
  }, []);

  const handleRandomize = useCallback(async () => {
    if (!isConfigured) {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const response = await getViewerItems({
        search: search.trim() || undefined,
        limit,
        random: true,
        favorites_only: favoritesOnly,
      });
      setItems(response.items);
      setTotal(response.total);
      setSelectedItem(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to shuffle TIFF files');
    } finally {
      setIsLoading(false);
    }
  }, [favoritesOnly, isConfigured, limit, search]);

  const handleCompositeChannelChange = useCallback(
    (color: ViewerChannelColor, value: number | null) => {
      setCompositeChannels((current) => ({
        ...current,
        [color]: value,
      }));
    },
    [],
  );

  const configuredChannelNames = config?.viewer_channel_names ?? [];
  const configuredDefaultChannel = clampChannel(
    config?.viewer_default_channel ?? 0,
    configuredChannelNames.length,
  );

  const handleExportContactSheet = useCallback(async () => {
    if (!isConfigured) {
      return;
    }
    setError(null);
    try {
      const blob = await exportViewerContactSheet({
        search: search.trim() || undefined,
        limit,
        favorites_only: favoritesOnly,
        render_mode: renderMode,
        single_channel: configuredDefaultChannel,
        composite_channels: compositeChannels,
        normalize: false,
      });
      downloadBlob(blob, `image-viewer-contact-sheet-${Date.now()}.png`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export contact sheet');
    }
  }, [
    compositeChannels,
    configuredDefaultChannel,
    favoritesOnly,
    isConfigured,
    limit,
    renderMode,
    search,
  ]);

  const handleMouseEnter = useCallback((item: ViewerItem, event: React.MouseEvent) => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }
    hoverTimeoutRef.current = window.setTimeout(() => {
      setHoveredItem(item);
      setHoverPosition({ x: event.clientX, y: event.clientY });
    }, 80);
  }, []);

  const handleMouseLeave = useCallback(() => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
    setHoveredItem(null);
  }, []);

  const handleMouseMove = useCallback((event: React.MouseEvent) => {
    setHoverPosition({ x: event.clientX, y: event.clientY });
  }, []);

  const handleChannelNameChange = useCallback((index: number, value: string) => {
    setChannelNames((current) => {
      const next = [...current];
      next[index] = value;
      return next;
    });
  }, []);

  const selected = selectedItem
    ? items.find((item) => item.id === selectedItem.id) ?? selectedItem
    : null;

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand-block">
          <span className="brand-logo" aria-hidden="true">
            AL
          </span>
          <div className="brand-title">
            <h1>Aldridge Lab</h1>
            <span className="brand-version">- {APP_VERSION}</span>
          </div>
          <span className="brand-context">Image Viewer</span>
          <span className="brand-status">
            {isConfigured ? `${total} TIFF files` : 'TIFF channel browser'}
          </span>
        </div>
        <div className="header-actions">
          <button
            className={`text-button ${showSetup ? 'is-active' : ''}`}
            type="button"
            onClick={() => setShowSetup((current) => !current)}
          >
            <Settings size={16} />
            Setup
            <ChevronDown size={16} className={showSetup ? 'rotate' : ''} />
          </button>
          {isConfigured && (
            <>
              <button
                className="icon-button"
                type="button"
                onClick={handleRefresh}
                disabled={isLoading}
                title="Refresh file list"
              >
                <RefreshCw size={17} className={isLoading ? 'spin' : ''} />
              </button>
              <button
                className="icon-button"
                type="button"
                onClick={handleClear}
                disabled={isLoading}
                title="Clear configuration"
              >
                <XCircle size={17} />
              </button>
            </>
          )}
        </div>
      </header>

      <main className="app-main">
        <SetupPanel
          isOpen={showSetup}
          directory={directory}
          pattern={pattern}
          channelNames={channelNames}
          defaultChannel={defaultChannel}
          inspectResult={inspectResult}
          isInspecting={isInspecting}
          isApplying={isApplying}
          onDirectoryChange={setDirectory}
          onPatternChange={setPattern}
          onInspect={handleInspect}
          onApply={handleApply}
          onChannelNameChange={handleChannelNameChange}
          onDefaultChannelChange={setDefaultChannel}
        />

        {error && <div className="error-banner">{error}</div>}

        {selected ? (
          <FullWindowViewer
            key={`${selected.id}-${configuredDefaultChannel}`}
            item={selected}
            items={items}
            channelNames={configuredChannelNames}
            initialChannel={configuredDefaultChannel}
            cacheKey={cacheKey}
            renderMode={renderMode}
            compositeChannels={compositeChannels}
            onClose={() => setSelectedItem(null)}
            onSelectItem={setSelectedItem}
            onFavoriteToggle={handleFavoriteToggle}
          />
        ) : (
          <section className="browser-shell">
            {isConfigured && (
              <BrowserToolbar
                search={search}
                limit={limit}
                favoritesOnly={favoritesOnly}
                isLoading={isLoading}
                renderMode={renderMode}
                compositeChannels={compositeChannels}
                channelNames={configuredChannelNames}
                channelCount={configuredChannelNames.length}
                onSearchChange={setSearch}
                onLimitChange={setLimit}
                onFavoritesOnlyChange={setFavoritesOnly}
                onRenderModeChange={setRenderMode}
                onCompositeChannelChange={handleCompositeChannelChange}
                onRandomize={handleRandomize}
                onExportContactSheet={handleExportContactSheet}
              />
            )}

            <div className="grid-region">
              {!isConfigured ? (
                <EmptyState
                  icon={FolderOpen}
                  title="No Directory Configured"
                  detail="Select a TIFF directory in setup."
                />
              ) : isLoading && items.length === 0 ? (
                <EmptyState icon={Loader2} title="Loading TIFF Files" spin />
              ) : items.length === 0 ? (
                <EmptyState
                  icon={FolderOpen}
                  title="No TIFF Files Found"
                  detail="Adjust the directory, pattern, or search filter."
                />
              ) : (
                <div className="image-grid">
                  {items.map((item) => (
                    <GridItem
                      key={item.id}
                      item={item}
                      channel={configuredDefaultChannel}
                      renderMode={renderMode}
                      compositeChannels={compositeChannels}
                      cacheKey={cacheKey}
                      onOpen={setSelectedItem}
                      onFavoriteToggle={handleFavoriteToggle}
                      onMouseEnter={handleMouseEnter}
                      onMouseLeave={handleMouseLeave}
                      onMouseMove={handleMouseMove}
                    />
                  ))}
                </div>
              )}
            </div>
          </section>
        )}
      </main>

      {isZKeyPressed && hoveredItem && !selected && (
        <ZoomPopup
          item={hoveredItem}
          channelNames={configuredChannelNames}
          mouseX={hoverPosition.x}
          mouseY={hoverPosition.y}
          cacheKey={cacheKey}
        />
      )}
    </div>
  );
}
