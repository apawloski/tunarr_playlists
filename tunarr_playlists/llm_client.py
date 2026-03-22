"""LLM client for generating themed movie lists."""

import json
import logging
import re
from typing import List, Dict, Any, Optional

import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = (
    "You are a movie recommendation engine. You return ONLY a JSON array of movie objects. "
    "Each object has exactly two keys: \"title\" (string, the official English-language release title) "
    "and \"year\" (integer, the release year). Do not include any text outside the JSON array. "
    "Do not include TV shows, short films, or documentaries unless explicitly asked. "
    "Ensure all recommendations are real, theatrically released films."
)


class LlmThemeClient:
    """Client for generating themed movie lists using an LLM."""

    def __init__(self, api_key: str):
        """Initialize LLM client.

        Args:
            api_key: Anthropic API key
        """
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate_movie_list(
        self,
        theme: str,
        count: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate a list of movies matching a theme.

        Args:
            theme: Description of the movie theme
            count: Number of movies to generate
            filters: Optional filters (year_min, year_max, min_rating)

        Returns:
            List of dicts with 'title' and 'year' keys
        """
        user_prompt = self._build_prompt(theme, count, filters)

        logger.info(f"Requesting {count} movies from LLM for theme: {theme}")

        try:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=4096,
                temperature=1.0,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}]
            )

            text = response.content[0].text
            movies = self._parse_response(text)

            logger.info(f"LLM returned {len(movies)} movies for theme: {theme}")
            return movies

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error generating movie list: {e}")
            return []

    def _build_prompt(
        self,
        theme: str,
        count: int,
        filters: Optional[Dict[str, Any]]
    ) -> str:
        """Build the user prompt for the LLM.

        Args:
            theme: Movie theme description
            count: Number of movies requested
            filters: Optional filters

        Returns:
            Formatted prompt string
        """
        parts = [f'Generate a list of {count} movies matching this theme: "{theme}"']

        if filters:
            if "year_min" in filters:
                parts.append(f"All movies must be released in or after {filters['year_min']}.")
            if "year_max" in filters:
                parts.append(f"All movies must be released in or before {filters['year_max']}.")
            if "min_rating" in filters:
                parts.append(
                    f"Only include movies generally considered to have a rating of "
                    f"{filters['min_rating']} or higher on a 10-point scale (e.g., IMDb)."
                )

        parts.append(
            f"Return exactly {count} movies as a JSON array. "
            f"If you cannot find {count} movies matching the theme, return as many as you can. "
            f"Do not repeat any title."
        )

        return "\n\n".join(parts)

    def _parse_response(self, text: str) -> List[Dict[str, Any]]:
        """Parse the LLM response into a list of movies.

        Args:
            text: Raw LLM response text

        Returns:
            List of validated movie dicts
        """
        # Try direct JSON parse first
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON array from response
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if not match:
                logger.error("Could not parse LLM response as JSON")
                logger.debug(f"Raw response: {text[:500]}")
                return []
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                logger.error("Could not parse extracted JSON array")
                return []

        if not isinstance(data, list):
            logger.error("LLM response is not a JSON array")
            return []

        # Validate each entry
        movies = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            title = entry.get("title")
            year = entry.get("year")
            if not isinstance(title, str) or not title:
                continue
            movie = {"title": title}
            if isinstance(year, int):
                movie["year"] = year
            movies.append(movie)

        return movies
