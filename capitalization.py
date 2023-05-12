from typing import TypeVar, Generic, List, Optional, Tuple, Set, Dict, Union, Iterable
from dataclasses import dataclass
from collections import deque


class ConsecutiveCapitalsAutomaton:
    _is_triggered = False
    _consecutive_capitals_count = 0

    def __init__(self, trigger_after=2):
        self._trigger_after = trigger_after

    def should_be_capital(self, c: str) -> bool:
        return c.isalpha() and c.isascii() and self._is_triggered

    def feed(self, c: str) -> None:
        if c == '\n' or c.islower():
            self._is_triggered = False

        if c.isupper():
            self._consecutive_capitals_count += 1
        else:
            self._consecutive_capitals_count = 0

        if self._consecutive_capitals_count == self._trigger_after:
            self._is_triggered = True


class SentenceStartCapitalsAutomaton:
    sentence_terminators = ['.', '?', '!']  # also double line-feed

    _is_waiting_for_sentence_start = True

    _found_dots = 0  # for finding non-capitalizing ellipsis
    _found_lf = 0  # for finding capitalizing paragraph

    def should_be_capital(self, c: str) -> bool:
        return c.isalpha() and c.isascii() and self._is_waiting_for_sentence_start and not self._found_dots >= 3  # no cap after ellipsis

    def feed(self, c: str) -> None:
        if c not in self.sentence_terminators and c != '\n':
            if c.isalpha() and c.isascii():
                self._reset()
            return

        if c == '.':
            self._found_dots += 1
            self._found_lf = 0
            self._is_waiting_for_sentence_start = True
        elif c == '!' or c == '?':
            self._found_dots = 0
            self._found_lf = 0
            self._is_waiting_for_sentence_start = True
        elif c == '\n':
            self._found_dots = 0
            self._found_lf += 1
            if self._found_lf >= 2:
                self._is_waiting_for_sentence_start = True

    def _reset(self):
        self._is_waiting_for_sentence_start = False
        self._found_dots = 0
        self._found_lf = 0


T = TypeVar('T')


class RingBuffer(Generic[T]):
    def __init__(self, capacity):
        self._capacity = capacity
        self._buf: List[Optional[T]] = [None] * capacity
        self._ptr = 0
        self._size = 0

    def add(self, elem: T) -> int:
        if len(self) == self._capacity:
            raise Exception('Buffer overflow')
        self._buf[self._ptr] = elem
        item_ptr = self._ptr
        self._ptr = (self._ptr + 1) % self._capacity
        self._size += 1
        return item_ptr

    def get_by_index(self, i) -> T:
        return self._buf[(self._ptr - self._size + i) % self._capacity]

    def get_by_pointer(self, ptr) -> T:
        return self._buf[ptr]

    def set_by_pointer(self, ptr, value):
        self._buf[ptr] = value

    def set_by_index(self, i, value):
        self._buf[(self._ptr - self._size + i) % self._capacity] = value

    def pop_last(self) -> T:
        if self._size == 0:
            raise Exception('Buffer is empty')
        item = self._buf[(self._ptr - self._size) % self._capacity]
        self._size -= 1
        return item

    def is_full(self):
        return len(self) == self._capacity

    def __len__(self):
        return self._size


@dataclass(frozen=True)
class ProperName:
    word: str
    from_pos: int


# That one hurt
class ProperNameCapitalsAutomaton:
    @dataclass
    class _ProperNameCandidate:
        word: str
        proper_name_score: int = 0

    class _NameCandidatesCache:
        def __init__(self, buffer_size=1000, proper_name_threshold=15, not_a_proper_name_threshold=-10):
            self._ring_buf = RingBuffer['ProperNameCapitalsAutomaton._ProperNameCandidate'](buffer_size)
            self._word_to_buffer_ptr = dict()
            self._proper_name_threshold = proper_name_threshold
            self._not_a_proper_name_threshold = not_a_proper_name_threshold

        def found_as_proper_name(self, word: str) -> Optional[str]:
            word_buffer_ptr = self._word_to_buffer_ptr.get(word)
            if word_buffer_ptr is not None:
                name_candidate = self._ring_buf.get_by_pointer(word_buffer_ptr)
                name_candidate.proper_name_score += 1
                if name_candidate.proper_name_score >= self._proper_name_threshold:
                    self._ring_buf.set_by_pointer(word_buffer_ptr, None)
                    del self._word_to_buffer_ptr[word]
                    return word
            else:
                if self._ring_buf.is_full():
                    popped_word = self._ring_buf.pop_last()
                    if popped_word is not None:
                        del self._word_to_buffer_ptr[popped_word.word]
                new_buffer_ptr = self._ring_buf.add(
                    ProperNameCapitalsAutomaton._ProperNameCandidate(word, proper_name_score=1))
                self._word_to_buffer_ptr[word] = new_buffer_ptr
                return None

        def found_as_maybe_not_proper_name(self, word: str):
            word_buffer_ptr = self._word_to_buffer_ptr.get(word)
            if word_buffer_ptr is None:
                return

            name_candidate = self._ring_buf.get_by_pointer(word_buffer_ptr)
            name_candidate.proper_name_score -= 1
            if name_candidate.proper_name_score <= self._not_a_proper_name_threshold:
                self._ring_buf.set_by_pointer(word_buffer_ptr, None)
                del self._word_to_buffer_ptr[word]

        def found_as_not_proper_name(self, word: str):
            word_buffer_ptr = self._word_to_buffer_ptr.get(word)
            if word_buffer_ptr is None:
                return

            self._ring_buf.set_by_pointer(word_buffer_ptr, None)
            del self._word_to_buffer_ptr[word]

    def __init__(self, buffer_size=10000, proper_name_threshold=10):
        self._proper_names: Dict[str, int] = {}
        self._name_candidates_cache = ProperNameCapitalsAutomaton._NameCandidatesCache(buffer_size,
                                                                                       proper_name_threshold,
                                                                                       not_a_proper_name_threshold=0)
        self._proper_name_threshold = proper_name_threshold

        self._pos = 0
        self._word = None
        self._word_start_pos = None
        self._word_is_proper_name = False

    def feed_get_output(self, c, c_is_predicted_capitalized) \
            -> Tuple[str, int, bool]:  # word, word_start_pos, is_in_automaton
        pos = self._pos
        self._pos += 1

        if not (c.isalpha() and c.isascii()):
            if c_is_predicted_capitalized:
                raise Exception('Non-alpha is predicted capitalized')
            if self._word is None:
                return c, pos, False

            (flushed_word, word_start) = self._flush_word()
            return flushed_word + c, word_start, flushed_word.lower() in self._proper_names
        else:  # c.isalpha()
            if self._word is not None:
                # extending word
                self._word.append(c)
            else:
                # new word
                self._word = [c]
                self._word_start_pos = pos
                self._word_is_proper_name = not c_is_predicted_capitalized and c.isupper()
            return '', 0, False

    def feed_end_and_get_output(self):
        (flushed_word, word_start) = self._flush_word()
        return flushed_word, word_start, flushed_word.lower() in self._proper_names

    def _flush_word(self) -> Tuple[str, int]:
        if self._word is None:
            return '', 0

        word = ''.join(self._word)
        word_pos = self._word_start_pos
        self._word = None
        self._word_start_pos = None
        if word[0].islower() and word[0].isascii():
            self._name_candidates_cache.found_as_not_proper_name(word)
        if not self._word_is_proper_name:
            self._name_candidates_cache.found_as_maybe_not_proper_name(word)
            return word, word_pos
        else:
            proper_name = word if word.lower() in self._proper_names else None
            if proper_name is not None:
                return word, word_pos

            proper_name = self._name_candidates_cache.found_as_proper_name(word)
            if proper_name is None:
                return word, word_pos
            else:
                self._proper_names[word.lower()] = word_pos
                return word, word_pos

    def get_proper_names(self) -> Set[ProperName]:
        return {ProperName(word, from_pos) for word, from_pos in self._proper_names.items()}


@dataclass
class CapitalizationData:
    proper_names: List[ProperName]
    rule_exceptions: List[int]

    def get_fmt(self):
        return f''


class Decapitalizer:
    def __init__(self):
        self._consecutive_capitals_automaton = ConsecutiveCapitalsAutomaton()
        self._sentence_start_automaton = SentenceStartCapitalsAutomaton()
        self._proper_names_automaton = ProperNameCapitalsAutomaton()
        self._pos = 0
        self._capitalization_rules_exception_positions = set()

    def feed(self, c: str) -> str:
        is_predicted_capitalized = self._consecutive_capitals_automaton.should_be_capital(c) \
                                   or self._sentence_start_automaton.should_be_capital(c)
        if (c.islower() and is_predicted_capitalized) or (c.isupper() and not is_predicted_capitalized):
            self._capitalization_rules_exception_positions.add(self._pos)

        self._consecutive_capitals_automaton.feed(c)
        self._sentence_start_automaton.feed(c)

        (last_word, last_word_pos, is_in_automaton) = self._proper_names_automaton.feed_get_output(c,
                                                                                                   is_predicted_capitalized)
        return self._process_proper_names_automaton_output(last_word, last_word_pos, is_in_automaton)

    def feed_end(self) -> str:
        (last_word, last_word_pos, is_in_automaton) = self._proper_names_automaton.feed_end_and_get_output()
        return self._process_proper_names_automaton_output(last_word, last_word_pos, is_in_automaton)

    def get_capitalization_data(self):
        proper_names = list(self._proper_names_automaton.get_proper_names())
        return CapitalizationData(proper_names, list(sorted(self._capitalization_rules_exception_positions)))

    def _process_proper_names_automaton_output(self, last_word, last_word_pos, is_in_automaton):
        if last_word is None or len(last_word) == 0:
            self._pos += 1
            return ''

        if len(last_word) != 1 and not (last_word[0].isalpha() and last_word[0].isascii()):
            raise Exception('Word doesnt start with alpha char')
        if is_in_automaton:
            if last_word[0].islower():
                self._capitalization_rules_exception_positions.add(last_word_pos)
            elif last_word[0].isupper():
                self._capitalization_rules_exception_positions.discard(last_word_pos)

        self._pos += 1
        return last_word.lower()


# блин, кое-как хватило на корявый кэш в декапитализаторе имён собственных, а тут еще и бор писать))
class WordTrie:
    class _State:
        state_id: int

        word_idx: Optional[int]

        depth: int
        next_states: Dict[str, 'WordTrie._State']

        def __init__(self, state_id, depth):
            self.state_id = state_id
            self.word_idx = None
            self.depth = depth
            self.next_states = {}

        def __hash__(self):
            return hash(self.state_id)

    def __init__(self):
        self._max_state_id = 0
        self._root = WordTrie._State(0, depth=0)
        self._word_not_from_trie_state = WordTrie._State(-1, depth=0)
        self._root.previous_state = self._root
        self._values = []
        self._current_state = None

    def add_word(self, word, value):
        word_id = len(self._values)
        self._values.append(value)

        state = self._root
        for c in word:
            next_state = state.next_states.get(c)
            if next_state is None:
                self._max_state_id += 1
                next_state = WordTrie._State(self._max_state_id, depth=state.depth + 1)
                state.next_states[c] = next_state
            state = next_state
        state.word_idx = word_id

    def finalize(self):
        self._current_state = self._root

    def move_and_get_value(self, c) -> Optional[ProperName]:
        next_state = self._current_state.next_states.get(c)
        if next_state is not None:  # moving down in original words trie
            self._current_state = next_state
            return None

        if c.isalpha() and c.isascii():  # new letter in word not from trie
            self._current_state = self._word_not_from_trie_state
            return None

        # finished word, maybe need to signal word from trie
        proper_name = self._values[self._current_state.word_idx] if self._current_state.word_idx is not None else None
        self._current_state = self._root
        return proper_name

    def get_depth(self):
        return self._current_state.depth


class Capitalizer:
    def __init__(self, capitalization_data: CapitalizationData):
        self._consecutive_capitals_automaton = ConsecutiveCapitalsAutomaton()
        self._sentence_start_automaton = SentenceStartCapitalsAutomaton()
        self._exception_positions = set(capitalization_data.rule_exceptions)
        self._pos = 0

        self._proper_names_automaton = WordTrie()
        for proper_name in capitalization_data.proper_names:
            self._proper_names_automaton.add_word(proper_name.word.lower(), proper_name)
        self._proper_names_automaton.finalize()

        max_proper_name_length = 1
        if len(capitalization_data.proper_names) > 0:
            max_proper_name_length = len(max(capitalization_data.proper_names, key=lambda name: len(name.word)).word)
        self._last_chars = RingBuffer(max_proper_name_length + 1)
        self._last_predictions = RingBuffer(max_proper_name_length + 1)

    def feed(self, c: str) -> str:
        self._last_chars.add(c)
        self._last_predictions.add(False)

        maybe_proper_name = self._proper_names_automaton.move_and_get_value(c)
        if maybe_proper_name is not None and self._pos >= maybe_proper_name.from_pos:
            self._last_predictions.set_by_index(len(self._last_predictions) - len(maybe_proper_name.word) - 1, True)

        max_buffer_length = self._proper_names_automaton.get_depth()
        returning_string = self._flush_buf(max_buffer_length) if max_buffer_length < len(self._last_chars) else ''
        self._pos += 1
        return returning_string

    def feed_end(self) -> str:
        return self._flush_buf(0)

    def in_(self, w):
        return w in self._exception_positions

    def _flush_buf(self, target_length: int):
        # print(target_length, len(self._last_chars) - target_length)
        buffer_length = len(self._last_chars)
        returning_chars = []
        for buffer_idx in range(len(self._last_chars) - target_length):
            returning_char = self._last_chars.pop_last()
            should_be_capitalized = self._last_predictions.pop_last()
            should_be_capitalized |= self._consecutive_capitals_automaton.should_be_capital(returning_char) \
                                     or self._sentence_start_automaton.should_be_capital(returning_char)

            pos_in_text = buffer_idx + self._pos - buffer_length + 1
            if self.in_(pos_in_text):
                should_be_capitalized = not should_be_capitalized

            if should_be_capitalized:
                returning_char = returning_char.upper()

            self._consecutive_capitals_automaton.feed(returning_char)
            self._sentence_start_automaton.feed(returning_char)

            returning_chars.append(returning_char)
        return ''.join(returning_chars)


def get_cap_data(iter_text: Iterable[str]) -> CapitalizationData:
    decapitalizer = Decapitalizer()
    for c in iter_text:
        next_seq = decapitalizer.feed(c)
    next_seq = decapitalizer.feed_end()
    return decapitalizer.get_capitalization_data()


def capitalize_iter(iter_chars: Iterable[str], cap_data: CapitalizationData) -> Iterable[str]:
    capitalizer = Capitalizer(cap_data)
    for c in iter_chars:
        next_seq = capitalizer.feed(c)
        if len(next_seq) > 0:
            yield next_seq

    next_seq = capitalizer.feed_end()
    if len(next_seq) > 0:
        yield next_seq


def decapitalize_iter(iter_text: Iterable[str]) -> Iterable[str]:
    for c in iter_text:
        yield c.lower()
