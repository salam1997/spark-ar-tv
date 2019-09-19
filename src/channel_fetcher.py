import json
import sys
import argparse

import config_factory
from site_config import DEVELOPER_KEY
from lib.api import ApiDataLoader
from lib.data_loader import *

def get_video_id(item):
    return item['id']['videoId']

def filter_videos(items, known_ids, keyword):
    result = []
    k = keyword.lower()
    for item in items:
        if item.id in known_ids:
            continue
        keep = False
        if k in item.title.lower():
            keep = True
        # tags
        if item.tags:
            for t in item.tags:
                if k in t:
                    keep = True
        if keep:
            result.append(item)
    return result

def fetch_all(config, master, lang, new_only = True, keyword="spark", max_result=10):
    api = ApiDataLoader(DEVELOPER_KEY)

    data_dir = "data/%s" % lang
    site = master.lang_sites[lang]
    all_ids = set(site.video_data.keys())
    skip_ids = set(load_skip_ids(data_dir))
    channels = set([(v.channel_id, v.channel_title) for v in site.video_data.values()])
    result = []

    print("Fetching channels...")
    channel_data = api.fetch_channels([c[0] for c in channels])
    for c in channel_data:
        print("Fetching %s(%s)..." % (c.title, c.playlist))
        items = api.fetch_playlist(c.playlist, max_result=max_result)
        items = filter_videos(items, all_ids.union(skip_ids), keyword)
        if len(items) > 0:
            result.append((c.title, items))
    
    if len(result) == 0:
        print("No new data")
        return master

    for v in result:
        print("# %s" % v[0])
        for item in v[1]:
            print("%s // %s" % (item.id, item.title))
        print()

    for v in result:
        for g in site.groups:
            if g.title == v[0]:
                for item in v[1]:
                    g.ids.append(item.id)
    # Reload video data
    all_youtube_ids = [id for g in site.groups for id in g.ids]
    site.video_data = load_video_data(all_youtube_ids, config.api_key)
    return master

def dump_site(site):
    lines = []
    groups = sorted(site.groups, key = lambda group: group.title.lower())
    for group in groups:
        lines.append("# %s" % group.title)
        for id in group.ids:
            lines.append("%s // %s" % (id, site.video_data[id].title))
        lines.append("")
    return lines

def cleanup(master):
    
    for site in master.lang_sites.values():
        lines = dump_site(site)
        # write back to data file
        with open("data/%s/data.txt" % site.lang, "w") as f:
            f.write('\n'.join(lines))
            print("Updated %s" % f.name)


def main():
    parser = argparse.ArgumentParser(description='Search video in channel')
    parser.add_argument('--id', type=str)
    parser.add_argument('--keyword', '-k', type=str, default="spark")
    parser.add_argument('--max', '-m', type=int, default=10)
    args = parser.parse_args()

    config = config_factory.load()
    master = master_site(config, merge_small_groups = False)

    if args.id is None:
        for lang in config.site_config.languages:
            print("==== Fetching %s ====" % lang)
            master = fetch_all(config, master, lang, keyword = args.keyword, max_result = args.max)
        cleanup(master)
    else:
        print("TODO fetch single channel")

if __name__=="__main__":
    main()
