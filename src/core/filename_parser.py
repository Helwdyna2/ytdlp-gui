"""Filename parsing logic for video file matching."""

import re
import logging
from typing import List, Tuple, Optional

from ..data.models import ParsedFilename

logger = logging.getLogger(__name__)

# Comprehensive list of known adult studios
KNOWN_STUDIOS = {
    # Vixen Media Group
    "vixen",
    "tushy",
    "blacked",
    "blackedraw",
    "tushy raw",
    "tushyraw",
    "blacked raw",
    "deeper",
    "slayed",
    # Nympho / Jules Jordan
    "nympho",
    "jules jordan",
    "julesjordan",
    "manuel ferrara",
    "manuelferrara",
    "the ass factory",
    # Brazzers Network
    "brazzers",
    "realitykings",
    "mofos",
    "babes",
    "twistys",
    "digitalplayground",
    "digital playground",
    "men",
    "seancody",
    "sean cody",
    "fakehub",
    "fakehospital",
    "faketaxi",
    # Bang Bros Network
    "bangbros",
    "bang bros",
    "bangbus",
    "backroomfacials",
    "bigmouthfuls",
    "bigtitcreamepie",
    "bigtitsroundasses",
    "brownbunnies",
    "chongas",
    "facialfest",
    # Naughty America
    "naughtyamerica",
    "naughty america",
    "myfriendshotmom",
    "my friends hot mom",
    "myfirstsexteacher",
    "housewife1on1",
    "housewife 1 on 1",
    "latinadultery",
    "dirtywivesclub",
    "neighborsaffair",
    # Evil Angel
    "evilangel",
    "evil angel",
    "jonni darkko",
    "jonnidarkko",
    "mike adriano",
    "mikeadriano",
    "rocco siffredi",
    "roccosiffredi",
    # Kink.com
    "kink",
    "hogtied",
    "devicebondage",
    "device bondage",
    "theupperfloor",
    "the upper floor",
    "publicdisgrace",
    "public disgrace",
    "hardcoregangbang",
    "hardcore gangbang",
    "boundgangbangs",
    "bound gangbangs",
    "sexandsubmission",
    "sex and submission",
    "thetrainingofo",
    # Team Skeet Network
    "teamskeet",
    "team skeet",
    "exxxtrasmall",
    "teenpies",
    "teen pies",
    "thisgirlsucks",
    "this girl sucks",
    "oyeloca",
    "povlife",
    "pov life",
    "tittyattack",
    "titty attack",
    "teenslovehugecocks",
    "teens love huge cocks",
    "cfnmteens",
    "cfnm teens",
    "innocenthigh",
    "innocent high",
    "shoplyfter",
    "dadcrush",
    "dad crush",
    "sislovesme",
    "sis loves me",
    "familystrokes",
    "family strokes",
    # Nubiles Network
    "nubiles",
    "nubilefilms",
    "nubiles films",
    "nubilesnet",
    "nubiles net",
    "nubilesunscripted",
    "nfbusty",
    "momsteachsex",
    "mom steach sex",
    "nubilesporn",
    "nubiles porn",
    "petitehdporn",
    "petite hd porn",
    "petiteballerinasfucked",
    # Mile High Media
    "sweetsinner",
    "sweet sinner",
    "realityjunkies",
    "reality junkies",
    "doghousefilms",
    "doghouse films",
    "iconmale",
    # Adult Time
    "adulttime",
    "adult time",
    "puretaboo",
    "pure taboo",
    "girlsway",
    "girls way",
    "burningangel",
    "burning angel",
    "fantasymassage",
    "fantasy massage",
    "allgirlmassage",
    "all girl massage",
    "nurumassage",
    "nuru massage",
    "soapymassage",
    "soapy massage",
    "milkingmassage",
    "milking massage",
    "21sextury",
    "21 sextury",
    "21naturals",
    "21 naturals",
    "21footart",
    "21 foot art",
    "dpfanatics",
    "dp fanatics",
    "assholefever",
    "asshole fever",
    # Porn Pros Network
    "pornpros",
    "porn pros",
    "passion-hd",
    "passionhd",
    "passion hd",
    "tiny4k",
    "lubed",
    "holed",
    "povd",
    "fantasyhd",
    "fantasy hd",
    "puremature",
    "pure mature",
    "castingcouch-x",
    "castingcouchx",
    "casting couch x",
    "myveryfirsttime",
    "my very first time",
    "exotic4k",
    "cum4k",
    # Misc Premium
    "x-art",
    "xart",
    "hegre",
    "metart",
    "met art",
    "metartx",
    "sexart",
    "sex art",
    "vivthomas",
    "viv thomas",
    "wow girls",
    "wowgirls",
    "joymii",
    "ultrafilms",
    "ultra films",
    "letsdoeit",
    "lets do it",
    "dorscel",
    "private",
    "penthouse",
    # Other Premium Studios
    "legalporno",
    "legal porno",
    "gonzo",
    "spizoo",
    "hardx",
    "hard x",
    "darkx",
    "dark x",
    "eroticax",
    "erotica x",
    "archangel",
    "wicked",
    "newsensations",
    "new sensations",
    "sweetheartvideo",
    "sweetheart video",
    # Reality / Amateur style
    "publicagent",
    "public agent",
    "fakecop",
    "fake cop",
    "sexwitmuslims",
    "czechcasting",
    "czech casting",
    "woodmancastingx",
    "woodman casting x",
    "exploitedcollegegirls",
    "girlsdoporn",
    "girls do porn",
    # Japanese
    "caribbeancom",
    "caribbean com",
    "1pondo",
    "tokyohot",
    "tokyo hot",
    "heyzo",
    # European
    "lesbea",
    "danejones",
    "dane jones",
    "momxxx",
    "mom xxx",
    "maturenl",
    "mature nl",
}

# Position/Act tags to preserve in renamed files
POSITION_TAGS = {
    # Positions
    "missionary",
    "doggy",
    "doggystyle",
    "doggy style",
    "cowgirl",
    "reverse cowgirl",
    "reversecowgirl",
    "spooning",
    "prone",
    "pronebone",
    "prone bone",
    "standing",
    "sideways",
    "69",
    "sixtynine",
    # Acts
    "bj",
    "blowjob",
    "blow job",
    "handjob",
    "hand job",
    "hj",
    "footjob",
    "foot job",
    "fj",
    "titjob",
    "titfuck",
    "tit fuck",
    "anal",
    "dp",
    "dvp",
    "dap",
    "tp",
    "gangbang",
    "gb",
    "threesome",
    "3some",
    "foursome",
    "4some",
    "orgy",
    "mff",
    "mmf",
    "ffm",
    "mfm",
    # Endings/Results
    "facial",
    "creampie",
    "internal",
    "swallow",
    "cim",
    "cip",
    "cumshot",
    "bukkake",
    "gokkun",
    # POV indicators
    "pov",
    # Scene parts
    "part1",
    "part2",
    "part3",
    "pt1",
    "pt2",
    "pt3",
    "part 1",
    "part 2",
    "part 3",
    "scene1",
    "scene2",
    "scene3",
    "sc1",
    "sc2",
    "sc3",
    "scene 1",
    "scene 2",
    "scene 3",
}

# Quality indicators to strip (not needed for database matching)
QUALITY_TAGS = {
    "1080p",
    "720p",
    "480p",
    "360p",
    "2160p",
    "4k",
    "uhd",
    "hd",
    "sd",
    "x264",
    "x265",
    "h264",
    "h265",
    "hevc",
    "avc",
    "web",
    "webrip",
    "webdl",
    "web-dl",
    "web dl",
    "mp4",
    "mkv",
    "avi",
    "wmv",
    "mov",
}


class FilenameParser:
    """Parse video filenames to extract searchable components."""

    def __init__(
        self,
        custom_studios: Optional[List[str]] = None,
        skip_keywords: Optional[List[str]] = None,
    ):
        """
        Initialize parser with optional custom studios.

        Args:
            custom_studios: Additional studio names to recognize
            skip_keywords: Keywords/phrases to strip from search parsing (preserved as tags)
        """
        self.studios = KNOWN_STUDIOS.copy()
        if custom_studios:
            self.studios.update(s.lower() for s in custom_studios)

        self._skip_keywords = {
            self._normalize_phrase(k) for k in (skip_keywords or []) if k and k.strip()
        }
        self._preserved_tag_set = POSITION_TAGS | self._skip_keywords
        self._max_preserved_tag_words = (
            max((len(t.split()) for t in self._preserved_tag_set), default=1) or 1
        )

    def parse(self, filename: str) -> ParsedFilename:
        """
        Parse a video filename to extract studio, performer, title, and tags.

        Algorithm:
        1. Remove file extension
        2. Normalize separators (replace . and _ with spaces, handle - specially)
        3. Extract and remove quality indicators (1080p, etc.)
        4. Extract and preserve position/act tags from end
        5. Identify studio (first segment or known studio match)
        6. Remaining text = potential performer + title combination
        7. Generate multiple search query variations

        Args:
            filename: The video filename to parse

        Returns:
            ParsedFilename object with extracted components
        """
        logger.debug(f"Parsing filename: {filename}")

        # Create result object
        result = ParsedFilename(original=filename)

        # Step 1: Remove file extension
        name_without_ext = self._remove_extension(filename)

        # Step 2: Normalize separators
        normalized = self._normalize_filename(name_without_ext)

        # Step 3: Extract and remove quality indicators
        normalized, quality_indicators = self._extract_quality_tags(normalized)
        result.quality_indicators = quality_indicators

        # Step 4: Extract and preserve position/act tags from end
        normalized, position_tags = self._extract_position_tags(normalized)
        result.preserved_tags = position_tags

        # Step 5: Split into segments (by dashes primarily)
        segments = [s.strip() for s in re.split(r"\s+-\s+", normalized) if s.strip()]

        # Step 6: Identify studio
        studio, remaining_segments = self._identify_studio(segments)
        result.studio = studio

        # Clean common date prefixes from remaining segments (yy mm dd / yyyy mm dd)
        remaining_segments = [
            self._strip_leading_date(s) for s in remaining_segments if s and s.strip()
        ]
        remaining_segments = [s for s in remaining_segments if s and s.strip()]

        # Step 7: Parse remaining segments for performer and title
        # If we have multiple segments left, first might be performer, rest is title
        if len(remaining_segments) >= 2:
            # Try to identify performer in first segment
            first_segment = remaining_segments[0]
            # Check if it looks like a name (2-3 capitalized words)
            if self._looks_like_name(first_segment):
                result.performers = [first_segment]
                result.title = " ".join(remaining_segments[1:])
            else:
                # Treat it all as title
                result.title = " ".join(remaining_segments)
        elif len(remaining_segments) == 1:
            result.title = remaining_segments[0]

        # Step 8: Generate search queries
        result.search_queries = self.generate_search_queries(result)

        logger.debug(
            f"Parsed result: studio={result.studio}, performers={result.performers}, "
            f"title={result.title}, tags={result.preserved_tags}"
        )

        return result

    def generate_search_queries(self, parsed: ParsedFilename) -> List[str]:
        """
        Generate search query variations ordered by specificity.

        Example for "Nympho - Aliya Brynn Aliya Is Your Fuckdoll - Missionary":
        1. "Aliya Is Your Fuckdoll" (just title)
        2. "Nympho Aliya Is Your Fuckdoll" (studio + title)
        3. "Aliya Brynn Aliya Is Your Fuckdoll" (performer + title)
        4. "Aliya Brynn" (just performer if no title match)

        Args:
            parsed: ParsedFilename object with extracted components

        Returns:
            List of search query strings, ordered by specificity
        """
        queries = []

        # Query 1: Just title (most specific if we have it)
        if parsed.title:
            queries.append(parsed.title)

        # Query 2: Studio + title
        if parsed.studio and parsed.title:
            queries.append(f"{parsed.studio} {parsed.title}")

        # Query 3: Performer + title
        if parsed.performers and parsed.title:
            performer = parsed.performers[0]  # Use first performer
            queries.append(f"{performer} {parsed.title}")

        # Query 4: Just performer (fallback if no good title)
        if parsed.performers:
            queries.append(parsed.performers[0])

        # Query 5: Studio + performer (another fallback)
        if parsed.studio and parsed.performers:
            queries.append(f"{parsed.studio} {parsed.performers[0]}")

        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            q_lower = q.lower()
            if q_lower not in seen:
                seen.add(q_lower)
                unique_queries.append(q)

        return unique_queries

    def _normalize_phrase(self, text: str) -> str:
        """Normalize a keyword/phrase for case-insensitive comparisons."""
        return " ".join(text.lower().strip().split())

    def _remove_extension(self, filename: str) -> str:
        """Remove file extension from filename."""
        extensions = [".mp4", ".mkv", ".avi", ".wmv", ".mov", ".flv", ".webm", ".m4v"]
        filename_lower = filename.lower()
        for ext in extensions:
            if filename_lower.endswith(ext):
                return filename[: -len(ext)]
        return filename

    def _normalize_filename(self, filename: str) -> str:
        """
        Normalize separators and clean up filename.

        Replace dots and underscores with spaces, but keep dashes as primary separator.
        """
        # Replace underscores and dots with spaces
        normalized = filename.replace("_", " ").replace(".", " ")

        # Clean up multiple spaces
        normalized = re.sub(r"\s+", " ", normalized)

        return normalized.strip()

    def _extract_quality_tags(self, text: str) -> Tuple[str, List[str]]:
        """Extract and remove quality indicators from text."""
        found_tags = []
        words = text.split()
        cleaned_words = []

        for word in words:
            word_lower = word.lower()
            # Remove common brackets/parentheses
            word_clean = word_lower.strip("()[]{}")

            if word_clean in QUALITY_TAGS:
                found_tags.append(word_clean)
            else:
                cleaned_words.append(word)

        cleaned_text = " ".join(cleaned_words)
        return cleaned_text, found_tags

    def _extract_position_tags(self, text: str) -> Tuple[str, List[str]]:
        """
        Extract position/act tags from end of filename.

        Returns:
            Tuple of (text without tags, list of tags found)
        """
        found_tags = []
        words = text.split()

        # Work backwards from end, collecting tags
        while words:
            matched_len = self._match_preserved_tag_length(words)
            if not matched_len:
                break

            found_tags.insert(0, " ".join(words[-matched_len:]))
            words = words[:-matched_len]

            # Remove trailing separator after tag removal (e.g., the "-" left behind from " - Tag")
            if words and words[-1] == "-":
                words = words[:-1]

        cleaned_text = " ".join(words)
        cleaned_text = re.sub(r"\s*-\s*$", "", cleaned_text).strip()
        return cleaned_text, found_tags

    def _match_preserved_tag_length(self, words: List[str]) -> Optional[int]:
        """
        Return the number of words that match a preserved tag at the end of `words`.

        Args:
            words: Tokenized filename parts.

        Returns:
            Number of tokens in matched tag, or None if no match.
        """
        max_len = min(self._max_preserved_tag_words, len(words))
        for length in range(max_len, 0, -1):
            candidate = self._normalize_phrase(" ".join(words[-length:]))
            if candidate in self._preserved_tag_set:
                return length
        return None

    def _identify_studio(self, segments: List[str]) -> Tuple[Optional[str], List[str]]:
        """
        Identify studio from filename segments.

        Returns:
            Tuple of (studio name or None, remaining segments)
        """
        if not segments:
            return None, []

        # Check if first segment matches known studio
        first_segment_lower = segments[0].lower()
        if first_segment_lower in self.studios:
            return segments[0], segments[1:]

        studio_match = self._extract_studio_from_segment(segments[0])
        if studio_match:
            studio_text, remainder = studio_match
            remaining = []
            if remainder:
                remaining.append(remainder)
            remaining.extend(segments[1:])
            return studio_text, remaining

        # If first segment looks like a studio name (single capitalized word or short phrase)
        # and we have more segments, assume it's the studio
        if len(segments) > 1 and len(segments[0].split()) <= 2:
            # Could be an unknown studio
            return segments[0], segments[1:]

        return None, segments

    def _extract_studio_from_segment(
        self, segment: str
    ) -> Optional[Tuple[str, str]]:
        """
        Extract a known studio from within a segment and return remainder.

        This supports filenames like:
            "nympho 25 11 12 sky pierce ..."

        Args:
            segment: First segment of the filename.

        Returns:
            Tuple of (studio_text, remainder_text) or None if no studio found.
        """
        segment_lower = segment.lower()

        best = None  # (start_index, -length, match, studio_key)
        for studio in self.studios:
            pattern = r"\b" + re.escape(studio).replace(r"\ ", r"\s+") + r"\b"
            match = re.search(pattern, segment_lower)
            if not match:
                continue
            candidate = (match.start(), -len(studio), match, studio)
            if best is None or candidate < best:
                best = candidate

        if best is None:
            return None

        match = best[2]
        studio_text = segment[match.start() : match.end()].strip()
        remainder = (segment[: match.start()] + segment[match.end() :]).strip()
        remainder = re.sub(r"\s+", " ", remainder).strip()
        return studio_text, remainder

    def _strip_leading_date(self, text: str) -> str:
        """
        Strip common date prefixes from a segment.

        Examples:
            "25 11 12 sky pierce" -> "sky pierce"
            "2026 01 14 xxlayna marie" -> "xxlayna marie"
        """
        cleaned = re.sub(r"^\d{4}\s+\d{2}\s+\d{2}\s+", "", text)
        cleaned = re.sub(r"^\d{2}\s+\d{2}\s+\d{2}\s+", "", cleaned)
        return cleaned.strip()

    def _looks_like_name(self, text: str) -> bool:
        """
        Check if text looks like a person's name.

        Heuristics:
        - 2-4 words
        - Each word starts with capital letter
        - Relatively short (under 30 chars)
        """
        words = text.split()

        if len(words) < 2 or len(words) > 4:
            return False

        if len(text) > 30:
            return False

        # Check if words look like names (start with capital)
        for word in words:
            if not word or not word[0].isupper():
                return False

        return True
