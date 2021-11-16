#!/usr/bin/env python3

# format GPX: https://fr.wikipedia.org/wiki/GPX_(format_de_fichier)

import gpxpy  # https://github.com/tkrajina/gpxpy
import gpxpy.gpx
from pathlib import Path
import json
import time
import datetime
import click
import simplekml


def gpx_info(gpx_file: Path, gpx, nautic, elevation):
    """Print GPX information."""

    if gpx.length_2d() == 0:
        print("empty track")
        return

    moving_data = gpx.get_moving_data()

    if moving_data.moving_time == 0:
        return

    start_time, end_time = gpx.get_time_bounds()
    delta = datetime.timedelta(seconds=moving_data.moving_time)
    points_no = len(list(gpx.walk(only_points=True)))

    def format_distance(distance: float) -> str:
        if nautic:
            return f"{distance / 1852:7.3f} NM"
        else:
            return f"{distance / 1000:7.3f} km"

    def format_speed(speed: float) -> str:
        if not speed:
            speed = 0
        if nautic:
            return f"{speed * 3600 / 1852:5.2f} kn"
        else:
            return f"{speed * 3600 / 1000:5.2f} km/h"

    def format_date(date: datetime.datetime, remove_date: datetime.datetime = None) -> str:
        now_timestamp = time.time()
        offset = datetime.datetime.fromtimestamp(now_timestamp) - datetime.datetime.utcfromtimestamp(now_timestamp)
        date += offset
        if remove_date and date.day == remove_date.day:
            return date.strftime("%H:%M:%S")
        else:
            return date.strftime("%Y-%m-%d %H:%M:%S")

    if elevation:
        # length = f"Length 3D: {format_distance( gpx.length_3d())}"
        length = f"{format_distance(gpx.length_3d())}"
    else:
        # length = f"Length 2D: {format_distance( gpx2.length_2d())}"
        length = f"{format_distance(gpx.length_2d())}"

    print(
        f"{gpx_file.name:<15}"
        f" ◇ Points: {points_no:5}"
        f" ◇ {length}"
        f" ◇ ⤒ {format_speed(moving_data.max_speed)}"  # max
        f" ◇ ≈ {format_speed(moving_data.moving_distance / moving_data.moving_time)}"  # average
        f" ◇ ⌚️ {format_date(start_time)} → {format_date(end_time, start_time)}"  # trip
        f" ◇ ⌛︎ {delta}"  # duration
    )


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("-e", "--elevation", help="Keep elevation", is_flag=True)
@click.option(
    "-r",
    "--reduce",
    help="Reduces the number of points (default: 1.0 m)",
    default=1.0,
    type=float,
)
@click.option("-s", "--simplify", help="Simplify tracks", is_flag=True)
@click.option("-S", "--smooth", help="Smooth tracks", is_flag=True)
@click.option("-n", "--nautic", help="Use nautic miles and knots", is_flag=True)
@click.option("-o", "--output", "output_name", help="Output file basename", default="merged")
@click.option("--gpx", "gpx_output", help="Write merged GPX (default: GeoJSON)", is_flag=True)
@click.option("--kml", "kml_output", help="Write merged KML", is_flag=True)
@click.argument("gpx_files", nargs=-1, type=click.Path(exists=True))
def main(
    elevation,
    reduce,
    simplify,
    smooth,
    nautic,
    output_name,
    gpx_output,
    kml_output,
    gpx_files,
):

    # merge GPX files
    if gpx_files:
        gpx_files = map(Path, gpx_files)
    else:
        gpx_files = Path(".").glob("nav*.gpx")

    merged = gpxpy.gpx.GPX()
    merged.name = output_name

    for gpx_file in gpx_files:

        gpx2 = gpxpy.parse(gpx_file.open())

        gpx_info(gpx_file, gpx2, nautic, elevation)

        for track in gpx2.tracks:

            gpx_track = gpxpy.gpx.GPXTrack()
            merged.tracks.append(gpx_track)

            gpx_track.name = f"{track.name} ({gpx_file})"
            gpx_track.description = track.description
            gpx_track.comment = track.comment
            gpx_track.source = track.source
            gpx_track.link = track.link
            gpx_track.link_text = track.link_text

            for segment in track.segments:

                # if we are not at see level
                if elevation:
                    segment.remove_elevation()

                if reduce and reduce > 0:
                    segment.reduce_points(reduce)

                if simplify:
                    segment.simplify()

                if smooth:
                    segment.smooth(horizontal=True)

                gpx_track.segments.append(segment)

    # show information about merged GPX
    gpx_info(Path(output_name), merged, nautic, elevation)

    # write merged GPX
    if kml_output:
        # in KML format
        kml = simplekml.Kml(open=1)

        for i, track in enumerate(merged.tracks, 1):
            linestring = kml.newlinestring(name=f"track{i}")
            if elevation and track.segments[0].points[0].elevation:
                coords = [
                    (point.longitude, point.latitude, point.elevation)
                    for segment in track.segments
                    for point in segment.points
                ]
                linestring.coords = coords
                linestring.altitudemode = simplekml.AltitudeMode.absolute
            else:
                coords = [(point.longitude, point.latitude) for segment in track.segments for point in segment.points]
                linestring.coords = coords
                linestring.altitudemode = simplekml.AltitudeMode.clamptoground

        kml.save(f"{output_name}.kml")

    elif gpx_output:
        # in GPX format
        Path(f"{output_name}.gpx").write_text(merged.to_xml())

    else:
        # in GeoJSON format

        def zdate(point: gpxpy.gpx.GPXTrackPoint) -> str:
            return point.time.strftime("%Y-%m-%dT%H:%M:%SZ")

        def coord(point: gpxpy.gpx.GPXTrackPoint) -> str:
            if elevation and point.elevation:
                return [
                    round(point.longitude, 9),
                    round(point.latitude, 9),
                    round(point.elevation, 3),
                ]
            else:
                return [round(point.longitude, 9), round(point.latitude, 9)]

        geojson = {"type": "FeatureCollection", "features": []}

        for i, track in enumerate(merged.tracks, 1):
            feature = {
                "type": "Feature",
                "properties": {
                    "trackNumber": i,
                    "name": track.name,
                    "desc": track.description,
                    "time": zdate(track.segments[0].points[0]),
                    "coordTimes": [zdate(point) for segment in track.segments for point in segment.points],
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [coord(point) for segment in track.segments for point in segment.points],
                },
            }

            geojson["features"].append(feature)

        json.dump(geojson, Path(f"{output_name}.geojson").open("w"), indent=2)


if __name__ == "__main__":
    main()
