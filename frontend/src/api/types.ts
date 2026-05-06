export interface ViewerInspectRequest {
  directory: string;
  pattern?: string;
}

export interface ViewerInspectResponse {
  total_images: number;
  sample_id: string | null;
  image_shape: number[] | null;
  axes: string | null;
  channel_count: number;
  default_channel_names: string[];
  detected_channel_names: string[];
  channel_name_source: 'metadata' | 'default';
}

export interface ViewerConfig {
  viewer_dir: string | null;
  viewer_pattern: string;
  viewer_channel_names: string[];
  viewer_default_channel: number;
  viewer_favorites_dir: string | null;
}

export interface ViewerConfigRequest {
  viewer_dir: string;
  viewer_pattern: string;
  viewer_channel_names: string[];
  viewer_default_channel: number;
  viewer_favorites_dir?: string | null;
}

export interface ViewerItem {
  id: string;
  filename: string;
  source_path: string;
  is_favorite: boolean;
  n_channels: number;
  shape: number[];
  dtype: string | null;
  axes: string | null;
  file_size_bytes: number | null;
  modified_time: number | null;
}

export interface ViewerItemsResponse {
  items: ViewerItem[];
  total: number;
}

export interface ViewerItemsRequest {
  search?: string;
  limit?: number;
  offset?: number;
  random?: boolean;
  seed?: number;
  favorites_only?: boolean;
}

export interface ImageRenderOptions {
  normalize?: boolean;
  cacheKey?: number;
}

export type ViewerRenderMode = 'single' | 'composite';

export type ViewerChannelColor = 'red' | 'green' | 'blue';

export interface ViewerCompositeChannels {
  red: number | null;
  green: number | null;
  blue: number | null;
}

export interface CompositeRenderOptions extends ImageRenderOptions {
  channels?: ViewerCompositeChannels;
  channelCount?: number;
}

export interface ViewerContactSheetExportRequest {
  item_ids?: string[];
  search?: string;
  limit?: number;
  favorites_only?: boolean;
  render_mode: ViewerRenderMode;
  single_channel?: number;
  composite_channels?: ViewerCompositeChannels;
  channel_names?: string[];
  normalize?: boolean;
}
