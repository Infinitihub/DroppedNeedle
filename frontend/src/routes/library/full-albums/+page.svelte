<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { ChevronLeft, Disc3, Search, X } from 'lucide-svelte';
	import { getLibraryFullAlbumsQuery } from '$lib/queries/library/LibraryQueries.svelte';
	import LibraryAlbumCard from '$lib/components/library/LibraryAlbumCard.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import type { AlbumSort } from '$lib/types';

	const PAGE_SIZE = 50;
	const SEARCH_DEBOUNCE_MS = 300;
	const VALID_SORTS: AlbumSort[] = ['recent', 'title', 'artist'];
	const FORMATS = ['flac', 'mp3', 'm4a', 'opus', 'ogg'];

	const params = $derived.by(() => {
		const searchParams = page.url.searchParams;
		const pageNum = Math.max(1, parseInt(searchParams.get('page') ?? '1', 10) || 1);
		const rawSort = (searchParams.get('sort') ?? 'recent') as AlbumSort;
		return {
			page: pageNum,
			sort: VALID_SORTS.includes(rawSort) ? rawSort : 'recent',
			q: searchParams.get('q') ?? '',
			format: searchParams.get('format') ?? ''
		};
	});

	const albumsQuery = getLibraryFullAlbumsQuery(() => params);
	const total = $derived(albumsQuery.data?.total ?? 0);
	const totalPages = $derived(
		albumsQuery.data ? Math.max(1, Math.ceil(albumsQuery.data.total / PAGE_SIZE)) : 1
	);

	let searchInput = $derived(params.q);
	let searchTimeout: ReturnType<typeof setTimeout> | undefined;
	$effect(() => () => clearTimeout(searchTimeout));

	function setParams(updates: Record<string, string | number | null>) {
		const url = new URL(page.url);
		for (const [key, value] of Object.entries(updates)) {
			if (value === null || value === '') url.searchParams.delete(key);
			else url.searchParams.set(key, String(value));
		}
		goto(url, { replaceState: true, keepFocus: true, noScroll: true });
	}

	function handleSearchInput(event: Event) {
		searchInput = (event.target as HTMLInputElement).value;
		clearTimeout(searchTimeout);
		searchTimeout = setTimeout(
			() => setParams({ q: searchInput.trim(), page: null }),
			SEARCH_DEBOUNCE_MS
		);
	}

	function clearSearch() {
		searchInput = '';
		clearTimeout(searchTimeout);
		setParams({ q: null, page: null });
	}
</script>

<svelte:head><title>Full Albums · Library</title></svelte:head>

<div class="container mx-auto p-4 md:p-6 lg:p-8">
	<div class="mb-6 flex items-center gap-4">
		<button
			class="btn btn-ghost btn-circle"
			onclick={() => goto('/library')}
			aria-label="Back to library"
		>
			<ChevronLeft class="h-6 w-6" />
		</button>
		<div>
			<h1 class="text-3xl font-bold">Full Albums</h1>
			<p class="mt-1 text-sm text-base-content/70">
				{total}
				{total === 1 ? 'album' : 'albums'}
			</p>
		</div>
	</div>

	<nav class="tabs tabs-boxed mb-5 w-fit" aria-label="Album views">
		<a href="/library/albums" class="tab">All Albums</a>
		<a href="/library/full-albums" class="tab tab-active" aria-current="page">Full Albums</a>
	</nav>

	<div class="mb-6 flex flex-col gap-3 sm:flex-row">
		<div class="group relative flex-1">
			<Search
				class="pointer-events-none absolute top-1/2 left-4 h-5 w-5 -translate-y-1/2 text-base-content/40 transition-colors duration-200 group-focus-within:text-primary"
			/>
			<input
				type="text"
				placeholder="Search full albums..."
				class="input input-bordered w-full rounded-full pr-12 pl-11"
				value={searchInput}
				oninput={handleSearchInput}
				aria-label="Search full albums"
			/>
			{#if searchInput}
				<button
					class="btn btn-ghost btn-circle btn-sm absolute top-1/2 right-3 -translate-y-1/2"
					onclick={clearSearch}
					aria-label="Clear search"
				>
					<X class="h-4 w-4" />
				</button>
			{/if}
		</div>
		<select
			class="select select-bordered rounded-full"
			value={params.sort}
			onchange={(event) =>
				setParams({ sort: (event.target as HTMLSelectElement).value, page: null })}
			aria-label="Sort full albums"
		>
			<option value="recent">Newest First</option>
			<option value="title">Title A-Z</option>
			<option value="artist">Artist A-Z</option>
		</select>
		<select
			class="select select-bordered rounded-full"
			value={params.format}
			onchange={(event) =>
				setParams({ format: (event.target as HTMLSelectElement).value, page: null })}
			aria-label="Filter by format"
		>
			<option value="">All formats</option>
			{#each FORMATS as format (format)}
				<option value={format}>{format.toUpperCase()}</option>
			{/each}
		</select>
	</div>

	{#if albumsQuery.isError}
		<div class="alert alert-error mb-6">
			<span>Couldn't load full albums</span>
			<button class="btn btn-ghost btn-sm" onclick={() => albumsQuery.refetch()}>Retry</button>
		</div>
	{:else if albumsQuery.isLoading}
		<div class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
			{#each Array(12) as _, index (`skeleton-${index}`)}
				<div class="skeleton aspect-square w-full rounded-lg"></div>
			{/each}
		</div>
	{:else if !albumsQuery.data || albumsQuery.data.items.length === 0}
		<div class="flex min-h-100 flex-col items-center justify-center text-center">
			<Disc3 class="mb-4 h-12 w-12 text-base-content/40" strokeWidth={1.5} />
			<h2 class="mb-2 text-2xl font-semibold">No full albums found</h2>
			<p class="text-base-content/70">
				{params.q || params.format
					? 'Try a different search or filter.'
					: 'Complete albums will appear here.'}
			</p>
		</div>
	{:else}
		<div class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
			{#each albumsQuery.data.items as album (album.id)}
				<LibraryAlbumCard {album} />
			{/each}
		</div>

		{#if totalPages > 1}
			<div class="mt-6 flex justify-center">
				<Pagination
					current={params.page}
					total={totalPages}
					onchange={(nextPage) => setParams({ page: nextPage })}
				/>
			</div>
		{/if}
	{/if}
</div>
