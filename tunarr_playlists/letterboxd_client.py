"""Letterboxd client for fetching movie lists."""

import logging
import re
from typing import List, Dict, Optional
import cloudscraper
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class LetterboxdClient:
    """Client for fetching Letterboxd lists."""

    def __init__(self):
        """Initialize Letterboxd client."""
        # Use cloudscraper to bypass Cloudflare/bot detection
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'desktop': True
            }
        )

    def get_list_movies(self, list_url: str) -> List[Dict[str, any]]:
        """Fetch all movies from a Letterboxd list.

        Args:
            list_url: URL of the Letterboxd list

        Returns:
            List of dictionaries with 'title' and optionally 'year' keys
        """
        movies = []
        page = 1
        base_url = list_url.rstrip('/')

        while True:
            if page == 1:
                url = base_url
            else:
                url = f"{base_url}/page/{page}/"

            logger.info(f"Fetching Letterboxd list page {page}: {url}")

            try:
                response = self.scraper.get(url, timeout=10)
                response.raise_for_status()
            except Exception as e:
                logger.error(f"Failed to fetch Letterboxd list page {page}: {e}")
                break

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all movie poster containers
            # Letterboxd uses <li class="posteritem"> for each movie (new structure)
            # Also try the old structure for backwards compatibility
            poster_containers = soup.find_all('li', class_='posteritem')
            if not poster_containers:
                poster_containers = soup.find_all('li', class_='poster-container')

            if not poster_containers:
                logger.info(f"No more movies found on page {page}")
                break

            for container in poster_containers:
                movie_data = self._parse_movie_container(container)
                if movie_data:
                    movies.append(movie_data)

            logger.info(f"Found {len(poster_containers)} movies on page {page}")

            # Check if there's a next page
            pagination = soup.find('div', class_='pagination')
            if not pagination or not pagination.find('a', class_='next'):
                break

            page += 1

        logger.info(f"Total movies fetched from Letterboxd list: {len(movies)}")
        return movies

    def _parse_movie_container(self, container) -> Optional[Dict[str, any]]:
        """Parse a movie container element.

        Args:
            container: BeautifulSoup element containing movie data

        Returns:
            Dictionary with movie data or None if parsing failed
        """
        try:
            # Try new structure first (posteritem with react-component)
            react_div = container.find('div', class_='react-component')
            if react_div:
                # New structure uses data-item-slug and data-item-name
                film_slug = react_div.get('data-item-slug')
                title_with_year = react_div.get('data-item-name')

                if not film_slug or not title_with_year:
                    return None

                # Extract year from title like "Sinners (2025)"
                year = None
                title = title_with_year
                year_match = re.search(r'\((\d{4})\)$', title_with_year)
                if year_match:
                    year = int(year_match.group(1))
                    # Remove year from title
                    title = title_with_year[:year_match.start()].strip()

                # Also try to extract from slug if not found
                if not year:
                    year_match = re.search(r'-(\d{4})$', film_slug)
                    if year_match:
                        year = int(year_match.group(1))

                movie_data = {
                    'title': title,
                    'slug': film_slug
                }

                if year:
                    movie_data['year'] = year

                logger.debug(f"Parsed movie: {title} ({year if year else 'unknown year'})")
                return movie_data

            # Fall back to old structure for backwards compatibility
            movie_div = container.find('div')
            if not movie_div:
                return None

            # Extract movie slug from data-film-slug attribute
            film_slug = movie_div.get('data-film-slug')
            if not film_slug:
                return None

            # Get the image element which contains the title in alt text
            img = movie_div.find('img')
            if not img:
                return None

            title = img.get('alt')
            if not title:
                return None

            # Try to extract year from the film slug or other attributes
            year = None
            year_match = re.search(r'-(\d{4})$', film_slug)
            if year_match:
                year = int(year_match.group(1))

            # Also check for data-film-year attribute
            if not year:
                year_str = movie_div.get('data-film-year')
                if year_str:
                    try:
                        year = int(year_str)
                    except ValueError:
                        pass

            movie_data = {
                'title': title,
                'slug': film_slug
            }

            if year:
                movie_data['year'] = year

            logger.debug(f"Parsed movie: {title} ({year if year else 'unknown year'})")
            return movie_data

        except Exception as e:
            logger.warning(f"Failed to parse movie container: {e}")
            return None
