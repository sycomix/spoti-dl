from dataclasses import dataclass

from yt_dlp import YoutubeDL
import yt_dlp

from spotidl.spotify import SpotifySong
from spotidl.utils import make_song_title, check_file


@dataclass
class YoutubeSong:
    """
    Umbrella for the song data extracted from Youtube.
    """

    id: str
    title: str
    video_url: str


def get_config(user_params: dict, song: SpotifySong) -> dict:
    """
    Prepares the parameters that need to be passed onto the YoutubeDL object.
    """

    downloader_params = {
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": user_params["codec"],
                "preferredquality": user_params["quality"],
            }
        ],
        "outtmpl": f"{make_song_title(song.artists, song.name, ', ')}.%(ext)s",
        # "outtmpl": "%(artist)s-%(title)s.ext",
        "quiet": user_params["quiet"],
        "format": "bestaudio/best",
        "dynamic_mpd": False,
        "noplaylist": True,
        "prefer_ffmpeg": True,
    }

    return downloader_params


def get_downloader(params: dict):
    """
    Initiates the YoutubeDL class with the configured parameters.
    """

    return YoutubeDL(params=params)


def fetch_source(ydl: YoutubeDL, song: SpotifySong) -> YoutubeSong:
    """
    Fetch appropriate source for the song from Youtube using the given details.
    """

    try:
        # adding "audio" to avoid 'official music videos' and similar types
        song_title = make_song_title(song.artists, song.name, ", ") + " audio"

        search: dict = ydl.extract_info(f"ytsearch:{song_title}", download=False)

        # extracting the first entry from the nested dict
        yt_info = search["entries"][0]

        # we are unable to find the song
        if song.name not in yt_info["title"]:
            print("\nCouldn't find the apt audio source with that name, retrying...")

            # retrying the search but with album name added
            song_title = (
                make_song_title(song.artists, song.name, ", ")
                + f" {song.album_name} audio"
            )

            search: dict = ydl.extract_info(f"ytsearch:{song_title}", download=False)

            yt_info = search["entries"][0]

            # now, if we are still getting the wrong result,
            # we should avoid the download
            return None

    except yt_dlp.DownloadError as exception:
        print("Error when trying to get audio source from YT: ", exception)
        return

    else:
        yt_song = YoutubeSong(
            id=yt_info["id"],
            title=yt_info["title"],
            video_url=yt_info["webpage_url"],
        )

        return yt_song


def download_song(ydl: YoutubeDL, link: str):
    """
    Downloads the song given its source link and the YouTube downloader object.
    """

    try:
        # attempts to download the song using the best matched
        # youtube source link
        ydl.download(link)

    except yt_dlp.DownloadError:
        print("\nDownload failed!")


def controller(user_params: dict, song: SpotifySong, file_name: str) -> bool:
    """
    Handles the flow of the download process for the given song.
    Initiates the configuration as per the user-defined parameters and chains
    the rest of functions together.
    """

    # check if song has already been downloaded before at some point;
    # only proceed with download if it doesn't
    if check_file(file_name):
        print(f"\n{file_name} already exists! Skipping download...\n")
        # False will ensure that we don't attempt to re-write metadata again
        return False

    else:
        # user parameters are used in the downloader parameters dictionary
        # the downloader_params dict is then passed onto the YoutubeDL object
        # when generating its instance.
        downloader_params = get_config(user_params, song)
        ydl = get_downloader(downloader_params)

        print(f"Starting '{song}' song download...\n")
        yt_song = fetch_source(ydl, song)

        if yt_song:
            download_song(ydl, yt_song.video_url)
        else:
            print("Couldn't find audio source for the song, skipping...\n")
            return False

        print(f"\nDownload for song '{song}' completed. Enjoy!")
        return True
