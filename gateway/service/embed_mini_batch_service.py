"""
file: gateway/service/embed_mini_batch_service.py

Service to create mini batches for embedding based on token cap
"""

from typing import Sequence
import tiktoken
from gateway.config.models import EmbedRowRequest, EmbedMiniBatch


class EmbedMiniBatchService:
    """Service for constructing token-aware embedding minibatches."""

    def __init__(
        self,
        *,
        model_name: str,
        max_request_tokens: int,
    ) -> None:
        """
        Initialize the minibatch service.

        Args:
            model_name: Embedding model name used to select tokenizer encoding.
            max_request_tokens: Maximum allowed token count per provider request.
        """

        # 1) Save configuration.
        self._model_name = model_name
        self._max_request_tokens = max_request_tokens

        # 2) Initialize tokenizer encoding.
        self._encoding = self._get_encoding(model_name=model_name)

    def build_minibatches(
        self,
        *,
        rows: Sequence[EmbedRowRequest],
    ) -> tuple[list[EmbedMiniBatch], list[EmbedRowRequest]]:
        """
        Build token-aware minibatches from request rows.

        Notes:
            - Token cost for each row is:
                tokens(student_answer_text) + tokens(feedback_text)
            - Rows that individually exceed the per-request token cap are dropped.
            - Rows are never split or truncated.

        Args:
            rows: Incoming proto request rows.

        Returns:
            A tuple containing:
                - list of minibatches
                - list of dropped oversize rows
        """

        # 1) Initialize outputs and accumulation state.
        minibatches: list[EmbedMiniBatch] = []
        dropped_rows: list[EmbedRowRequest] = []

        current_rows: list[EmbedRowRequest] = []
        current_tokens = 0
        batch_index = 0

        # 2) Iterate rows in original order.
        for row in rows:
            row_tokens = self._count_row_tokens(row=row)

            # 3) Drop the row entirely if it exceeds the request cap by itself.
            if row_tokens > self._max_request_tokens:
                dropped_rows.append(row)
                continue

            # 4) Flush current minibatch if adding this row would exceed the cap.
            if current_rows and (current_tokens + row_tokens) > self._max_request_tokens:
                minibatches.append(
                    EmbedMiniBatch(
                        batch_index=batch_index,
                        rows=current_rows,
                        total_tokens=current_tokens,
                    )
                )
                batch_index += 1
                current_rows = []
                current_tokens = 0

            # 5) Add row to current minibatch.
            current_rows.append(row)
            current_tokens += row_tokens

        # 6) Flush the final minibatch if present.
        if current_rows:
            minibatches.append(
                EmbedMiniBatch(
                    batch_index=batch_index,
                    rows=current_rows,
                    total_tokens=current_tokens,
                )
            )

        # 7) Return minibatches plus dropped rows.
        return minibatches, dropped_rows

    def _count_row_tokens(
        self,
        *,
        row: EmbedRowRequest,
    ) -> int:
        """
        Count the estimated token cost of a request row.

        Args:
            row: Proto request row.

        Returns:
            Total estimated token count for the row.
        """

        # 1) Count tokens in student answer text.
        student_tokens = len(self._encoding.encode(row.student_answer_text))

        # 2) Count tokens in feedback text.
        feedback_tokens = len(self._encoding.encode(row.feedback_text))

        # 3) Return combined row token cost.
        return student_tokens + feedback_tokens

    @staticmethod
    def _get_encoding(model_name: str):
        """
        Resolve tokenizer encoding for a model.

        Args:
            model_name: OpenAI model name.

        Returns:
            Tokenizer encoding object.
        """

        # 1) Attempt model-specific encoding resolution.
        try:
            return tiktoken.encoding_for_model(model_name)
        except KeyError:
            # 2) Fall back to cl100k_base if the model is unknown to tiktoken.
            return tiktoken.get_encoding("cl100k_base")
