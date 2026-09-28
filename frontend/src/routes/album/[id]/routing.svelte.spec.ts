import { beforeEach, expect, it, vi } from 'vitest';
import { render } from 'vitest-browser-svelte';

const h = vi.hoisted(() => ({
	goto: vi.fn(),
	cache: vi.fn().mockResolvedValue(undefined),
	localView: vi.fn(),
	providerView: vi.fn(),
	localDetailRequest: vi.fn(),
	localDetail404: false,
	album: {
		id: 'local-album-id',
		musicbrainz_release_group_id: 'provider-album-id' as string | null
	}
}));

vi.mock('$app/navigation', () => ({
	goto: (...args: unknown[]) => h.goto(...args)
}));

vi.mock('./LocalAlbumPage.svelte', () => {
	const Component = function (props: unknown) {
		h.localView(props);
	};
	Component.prototype = {};
	return { default: Component };
});

vi.mock('./ProviderAlbumPage.svelte', () => {
	const Component = function (_anchor: unknown, props: { data: unknown; localAlbum?: unknown }) {
		h.providerView(props);
	};
	Component.prototype = {};
	return { default: Component };
});

vi.mock('$lib/queries/library/LibraryQueries.svelte', async (importOriginal) => ({
	...(await importOriginal<typeof import('$lib/queries/library/LibraryQueries.svelte')>()),
	getLibraryAlbumDetailQuery: (...args: unknown[]) => {
		h.localDetailRequest(...args);
		return h.localDetail404
			? { data: undefined, isLoading: false, isError: true, error: new Error('404') }
			: { data: h.album, isLoading: false, isError: false, error: null };
	},
	cacheCanonicalLibraryAlbumDetail: (...args: unknown[]) => h.cache(...args)
}));

import AlbumPage from './+page.svelte';

beforeEach(() => {
	vi.clearAllMocks();
	h.album.id = 'local-album-id';
	h.album.musicbrainz_release_group_id = 'provider-album-id';
	h.localDetail404 = false;
});

it('keeps a linked album on its MusicBrainz release-group route', async () => {
	h.album.id = 'provider-album-id';
	await render(AlbumPage, {
		props: { data: { albumId: 'provider-album-id' } }
	} as unknown as Parameters<typeof render>[1]);

	await vi.waitFor(() => expect(h.goto).not.toHaveBeenCalled());
	expect(h.cache).not.toHaveBeenCalled();
	expect(h.providerView).toHaveBeenCalledWith(expect.objectContaining({ localAlbum: h.album }));
	expect(h.localView).not.toHaveBeenCalled();
});

it('shows a linked album on its MusicBrainz route without redirecting to itself', async () => {
	await render(AlbumPage, {
		props: { data: { albumId: 'provider-album-id' } }
	} as unknown as Parameters<typeof render>[1]);

	await vi.waitFor(() =>
		expect(h.providerView).toHaveBeenCalledWith(expect.objectContaining({ localAlbum: h.album }))
	);
	expect(h.goto).not.toHaveBeenCalled();
	expect(h.localView).not.toHaveBeenCalled();
});

it('redirects a retired local album id to its MusicBrainz route', async () => {
	await render(AlbumPage, {
		props: { data: { albumId: 'retired-album-id' } }
	} as unknown as Parameters<typeof render>[1]);

	await vi.waitFor(() =>
		expect(h.goto).toHaveBeenCalledWith(expect.stringContaining('provider-album-id'), {
			replaceState: true
		})
	);
});

it('mounts the provider once when local detail returns 404', async () => {
	h.localDetail404 = true;
	await render(AlbumPage, {
		props: { data: { albumId: 'provider-album-id' } }
	} as unknown as Parameters<typeof render>[1]);

	await vi.waitFor(() => expect(h.providerView).toHaveBeenCalledTimes(1));
	expect(h.localDetailRequest).toHaveBeenCalledTimes(1);
	expect(h.providerView).toHaveBeenCalledWith(expect.objectContaining({ localAlbum: undefined }));
});

it('keeps a linked local route local for copy workflows', async () => {
	await render(AlbumPage, {
		props: { data: { albumId: 'local-album-id' } }
	} as unknown as Parameters<typeof render>[1]);

	await vi.waitFor(() => expect(h.goto).not.toHaveBeenCalled());
	expect(h.cache).not.toHaveBeenCalled();
	expect(h.providerView).not.toHaveBeenCalled();
	expect(h.localView).toHaveBeenCalled();
});

it('keeps a local-only album on its local route', async () => {
	h.album.musicbrainz_release_group_id = null;
	await render(AlbumPage, {
		props: { data: { albumId: 'local-album-id' } }
	} as unknown as Parameters<typeof render>[1]);

	await vi.waitFor(() => expect(h.goto).not.toHaveBeenCalled());
	expect(h.localView).toHaveBeenCalled();
	expect(h.providerView).not.toHaveBeenCalled();
});
