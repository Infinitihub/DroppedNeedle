import pytest

from services.exportify_import_service import (
    InvalidExportifyFileError,
    parse_exportify_csv,
)


def test_parse_exportify_csv_maps_documented_columns():
    data = (
        "Track Name,Artist Name(s),Album Name,Disc Number,Track Number,"
        "Track Duration (ms),ISRC,Album Image URL\n"
        "Song,Artist,Album,2,4,185000,US-ABC-12-34567,https://image.test/a.jpg\n"
    ).encode()

    assert parse_exportify_csv(data) == [
        {
            "track_name": "Song",
            "artist_name": "Artist",
            "album_name": "Album",
            "album_artist_name": "",
            "isrc": "US-ABC-12-34567",
            "album_image": "https://image.test/a.jpg",
            "track_number": 4,
            "disc_number": 2,
            "duration": 185,
        }
    ]


def test_parse_exportify_csv_accepts_utf8_bom_and_skips_blank_rows():
    data = "\ufeffTrack Name,Artist Name(s),Album Name\nSong,Artist,Album\n,,\n".encode()

    assert len(parse_exportify_csv(data)) == 1


def test_parse_exportify_csv_rejects_missing_columns():
    with pytest.raises(InvalidExportifyFileError, match="Missing Exportify columns"):
        parse_exportify_csv(b"Track Name,Artist Name(s)\nSong,Artist\n")


def test_parse_exportify_csv_rejects_empty_export():
    with pytest.raises(InvalidExportifyFileError, match="no usable tracks"):
        parse_exportify_csv(b"Track Name,Artist Name(s),Album Name\n,,\n")