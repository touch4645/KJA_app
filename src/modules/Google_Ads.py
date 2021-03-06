#!/usr/bin/env python
# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""This example generates keyword ideas from a list of seed keywords."""


import argparse
import sys
from google.ads.google_ads.client import GoogleAdsClient
from google.ads.google_ads.errors import GoogleAdsException

# Location IDs are listed here: https://developers.google.com/adwords/api/docs/appendix/geotargeting
# and they can also be retrieved using the GeoTargetConstantService as shown
# here: https://developers.google.com/google-ads/api/docs/targeting/location-targeting
_DEFAULT_LOCATION_IDS = ["2392"]  # location ID for Japan
# A language criterion ID. For example, specify 1000 for English. For more
# information on determining this value, see the below link:
# https://developers.google.com/adwords/api/docs/appendix/codes-formats#languages.
_DEFAULT_LANGUAGE_ID = "1005"  # language ID for Japanese


def main(
    client, customer_id, location_ids, language_id, keyword_texts, page_url
):
    keyword_plan_idea_service = client.get_service(
        "KeywordPlanIdeaService", version="v5"
    )
    keyword_competition_level_enum = client.get_type(
        "KeywordPlanCompetitionLevelEnum", version="v5"
    ).KeywordPlanCompetitionLevel
    month_of_year_enum = client.get_type(
        "MonthOfYearEnum", version="v5"
    ).MonthOfYear
    keyword_plan_network = client.get_type(
        "KeywordPlanNetworkEnum", version="v5"
    ).GOOGLE_SEARCH_AND_PARTNERS
    locations = map_locations_to_string_values(client, location_ids)
    language = map_language_to_string_value(client, language_id)
    page_size = 100

    # Only one of these values will be passed to the KeywordPlanIdeaService
    # depending on whether keywords, a page_url or both were given.
    url_seed = None
    keyword_seed = None
    keyword_url_seed = None

    # Either keywords or a page_url are required to generate keyword ideas
    # so this raises an error if neither are provided.
    if not (keyword_texts or page_url):
        raise ValueError(
            "At least one of keywords or page URL is required, "
            "but neither was specified."
        )

    # To generate keyword ideas with only a page_url and no keywords we need
    # to initialize a UrlSeed object with the page_url as the "url" field.
    if not keyword_texts and page_url:
        url_seed = client.get_type("UrlSeed", version="v5")
        url_seed.url.value = page_url

    # To generate keyword ideas with only a list of keywords and no page_url
    # we need to initialize a KeywordSeed object and set the "keywords" field
    # to be a list of StringValue objects.
    if keyword_texts and not page_url:
        keyword_seed = client.get_type("KeywordSeed", version="v5")
        keyword_protos = map_keywords_to_string_values(client, keyword_texts)
        keyword_seed.keywords.extend(keyword_protos)

    # To generate keyword ideas using both a list of keywords and a page_url we
    # need to initialize a KeywordAndUrlSeed object, setting both the "url" and
    # "keywords" fields.
    if keyword_texts and page_url:
        keyword_url_seed = client.get_type("KeywordAndUrlSeed", version="v5")
        keyword_url_seed.url.value = page_url
        keyword_protos = map_keywords_to_string_values(client, keyword_textss)
        keyword_url_seed.keywords.extend(keyword_protos)

    try:
        keyword_ideas = keyword_plan_idea_service.generate_keyword_ideas(
            customer_id,
            language,
            locations,
            False,
            keyword_plan_network,
            page_size,
            url_seed=url_seed,
            keyword_seed=keyword_seed,
            keyword_and_url_seed=keyword_url_seed,
        )
        result = {}

        for idea in keyword_ideas:
            competition_value = keyword_competition_level_enum.Name(
                idea.keyword_idea_metrics.competition
            )

            monthly_search_volumes = {}
            search_volumes = idea.keyword_idea_metrics.monthly_search_volumes
            for index in range(12):
                month = month_of_year_enum.Name(search_volumes[index].month)
                year = search_volumes[index].year.value
                value = search_volumes[index].monthly_searches.value

                year_to_month = month_to_integer_values(month, year)
                monthly_search_volumes[year_to_month] = {
                    "value": value
                }

            result[idea.text.value] = {
                "avg_monthly_searches_volume": idea.keyword_idea_metrics.avg_monthly_searches.value,
                "monthly_search_volumes": monthly_search_volumes,
                "competition": {
                    "level": competition_value,
                    "value": idea.keyword_idea_metrics.competition_index.value
                }
            }
        return result

    except GoogleAdsException as ex:
        print(
            f'Request with ID "{ex.request_id}" failed with status '
            f'"{ex.error.code().name}" and includes the following errors:'
        )
        for error in ex.failure.errors:
            print(f'\tError with message "{error.message}".')
            if error.location:
                for field_path_element in error.location.field_path_elements:
                    print(f"\t\tOn field: {field_path_element.field_name}")
        sys.exit(1)
        return False


def month_to_integer_values(month, year):
    month_to_int = {
        "JANUARY": "/1",
        "FEBRUARY": "/2",
        "MARCH": "/3",
        "APRIL": "/4",
        "MAY": "/5",
        "JUNE": "/6",
        "JULY": "/7",
        "AUGUST": "/8",
        "SEPTEMBER": "/9",
        "OCTOBER": "/10",
        "NOVEMBER": "/11",
        "DECEMBER": "/12"
    }
    return str(year) + month_to_int[month]


def map_keywords_to_string_values(client, keyword_texts):
    keyword_protos = []
    for keyword in keyword_texts:
        string_val = client.get_type("StringValue", version="v5")
        string_val.value = keyword
        keyword_protos.append(string_val)
    return keyword_protos


def map_locations_to_string_values(client, location_ids):
    gtc_service = client.get_service("GeoTargetConstantService", version="v5")
    locations = []
    for location_id in location_ids:
        location = client.get_type("StringValue", version="v5")
        location.value = gtc_service.geo_target_constant_path(location_id)
        locations.append(location)
    return locations


def map_language_to_string_value(client, language_id):
    language = client.get_type("StringValue")
    language.value = client.get_service(
        "LanguageConstantService", version="v5"
    ).language_constant_path(language_id)
    return language


def get_keywords_data(
        customer_id, location_ids, language_id, keyword_texts, page_url
):
    # GoogleAdsClient will read the google-ads.yaml configuration file in the
    # home directory if none is specified.

    # Heroku env
    google_ads_client = GoogleAdsClient.load_from_storage('/app/google-ads.yaml')
    # local Docker env
    # google_ads_client = GoogleAdsClient.load_from_storage('/home/KJA_APP/google-ads.yaml')
    return main(google_ads_client, customer_id, location_ids, language_id, keyword_texts, page_url)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generates keyword ideas from a list of seed keywords."
    )

    # The following argument(s) should be provided to run the example.
    parser.add_argument(
        "-c",
        "--customer_id",
        type=str,
        required=True,
        help="The Google Ads customer ID.",
    )
    parser.add_argument(
        "-k",
        "--keyword_texts",
        nargs="+",
        type=str,
        required=False,
        default=[],
        help="Space-delimited list of starter keywords",
    )
    # To determine the appropriate location IDs, see:
    # https://developers.google.com/adwords/api/docs/appendix/geotargeting.
    parser.add_argument(
        "-l",
        "--location_ids",
        nargs="+",
        type=str,
        required=False,
        default=_DEFAULT_LOCATION_IDS,
        help="Space-delimited list of location criteria IDs",
    )
    # To determine the appropriate language ID, see:
    # https://developers.google.com/adwords/api/docs/appendix/codes-formats#languages.
    parser.add_argument(
        "-i",
        "--language_id",
        type=str,
        required=False,
        default=_DEFAULT_LANGUAGE_ID,
        help="The language criterion ID.",
    )
    # Optional: Specify a URL string related to your business to generate ideas.
    parser.add_argument(
        "-p",
        "--page_url",
        type=str,
        required=False,
        help="A URL string related to your business",
    )

    args = parser.parse_args()

    get_keywords_data(
        args.customer_id,
        args.location_ids,
        args.language_id,
        args.keyword_texts,
        args.page_url,
    )