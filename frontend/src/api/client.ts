import type {
  CompositeRenderOptions,
  ImageRenderOptions,
  ViewerChannelColor,
  ViewerConfig,
  ViewerConfigRequest,
  ViewerContactSheetExportRequest,
  ViewerInspectRequest,
  ViewerInspectResponse,
  ViewerItemsRequest,
  ViewerItemsResponse,
} from './types';

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api';
const COMPOSITE_CHANNEL_KEYS: ViewerChannelColor[] = ['red', 'green', 'blue'];

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    let message = body;
    try {
      const parsed = JSON.parse(body) as { detail?: string };
      message = parsed.detail ?? body;
    } catch {
      message = body;
    }
    throw new Error(message || `API error ${response.status}`);
  }

  return response.json() as Promise<T>;
}

async function fetchBlobApi(endpoint: string, options?: RequestInit): Promise<Blob> {
  const headers = new Headers(options?.headers);
  if (options?.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const body = await response.text();
    let message = body;
    try {
      const parsed = JSON.parse(body) as { detail?: string };
      message = parsed.detail ?? body;
    } catch {
      message = body;
    }
    throw new Error(message || `API error ${response.status}`);
  }

  return response.blob();
}

function appendImageRenderParams(params: URLSearchParams, options: ImageRenderOptions): void {
  if (options.normalize !== undefined) {
    params.set('normalize', options.normalize ? 'true' : 'false');
  }
  if (options.cacheKey !== undefined) {
    params.set('v', String(options.cacheKey));
  }
}

function isValidCompositeChannel(
  channel: number | null | undefined,
  channelCount?: number,
): channel is number {
  return (
    channel !== null &&
    channel !== undefined &&
    Number.isInteger(channel) &&
    channel >= 0 &&
    (channelCount === undefined || channel < channelCount)
  );
}

function buildViewerCompositeEndpoint(itemId: string, options: CompositeRenderOptions = {}): string {
  const params = new URLSearchParams();
  appendImageRenderParams(params, options);
  for (const color of COMPOSITE_CHANNEL_KEYS) {
    const channel = options.channels?.[color];
    if (isValidCompositeChannel(channel, options.channelCount)) {
      params.set(`${color}_channel`, String(channel));
    }
  }
  const query = params.toString();
  return `/viewer/composite/${encodeURIComponent(itemId)}${query ? `?${query}` : ''}`;
}

export async function inspectViewerDir(
  request: ViewerInspectRequest,
): Promise<ViewerInspectResponse> {
  return fetchApi<ViewerInspectResponse>('/viewer/inspect', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getViewerConfig(): Promise<ViewerConfig> {
  return fetchApi<ViewerConfig>('/viewer/config');
}

export async function setViewerConfig(
  request: ViewerConfigRequest,
): Promise<ViewerConfig> {
  return fetchApi<ViewerConfig>('/viewer/config', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getViewerItems(
  request: ViewerItemsRequest = {},
): Promise<ViewerItemsResponse> {
  const params = new URLSearchParams();
  if (request.search) params.set('search', request.search);
  if (request.limit !== undefined) params.set('limit', String(request.limit));
  if (request.offset !== undefined) params.set('offset', String(request.offset));
  if (request.random) params.set('random', 'true');
  if (request.seed !== undefined) params.set('seed', String(request.seed));
  if (request.favorites_only) params.set('favorites_only', 'true');
  const query = params.toString();
  return fetchApi<ViewerItemsResponse>(`/viewer/items${query ? `?${query}` : ''}`);
}

export function getViewerImageUrl(
  itemId: string,
  channel: number,
  options: ImageRenderOptions = {},
): string {
  const params = new URLSearchParams();
  appendImageRenderParams(params, options);
  const query = params.toString();
  return `${API_BASE}/viewer/image/${encodeURIComponent(itemId)}/${channel}${query ? `?${query}` : ''}`;
}

export function getViewerCompositeUrl(
  itemId: string,
  options: CompositeRenderOptions = {},
): string {
  return `${API_BASE}${buildViewerCompositeEndpoint(itemId, options)}`;
}

export async function getViewerCompositePng(
  itemId: string,
  options: CompositeRenderOptions = {},
): Promise<Blob> {
  return fetchBlobApi(buildViewerCompositeEndpoint(itemId, options));
}

export async function exportViewerContactSheet(
  request: ViewerContactSheetExportRequest,
): Promise<Blob> {
  return fetchBlobApi('/viewer/export/contact-sheet', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function toggleViewerFavorite(
  itemId: string,
  favorite: boolean,
): Promise<{ status: string; id: string; is_favorite: boolean }> {
  return fetchApi(`/viewer/item/${encodeURIComponent(itemId)}/favorite`, {
    method: 'POST',
    body: JSON.stringify({ favorite }),
  });
}

export async function refreshViewerFiles(): Promise<{ status: string; total: number }> {
  return fetchApi('/viewer/refresh', { method: 'POST' });
}

export async function clearViewerConfig(): Promise<ViewerConfig> {
  return fetchApi<ViewerConfig>('/viewer/clear', { method: 'POST' });
}
