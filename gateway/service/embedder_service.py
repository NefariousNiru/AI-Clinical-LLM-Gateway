"""
file: gateway/service/embedder_service.py

gRPC embedding service for batched row-level embedding requests.

Responsibilities:
    1) Validate incoming embedding batch requests.
    2) Build token-aware minibatches through EmbedMiniBatchService.
    3) Execute minibatches concurrently against OpenAI embeddings.
    4) Respect request-window rate limiting through RequestWindowLimiter.
    5) Retry provider calls on rate limiting.
    6) Return row-aligned embedding responses.

Notes:
    - This service is OpenAI-only.
    - The embedding model is fixed to `text-embedding-3-large`.
    - Minibatching is based on the combined token count of:
        student_answer_text + feedback_text
      for each row.
    - A row that exceeds the configured per-request token cap by itself is dropped.
"""

import asyncio
import logging
import time
from typing import Sequence
import grpc
from openai import AsyncOpenAI, RateLimitError
from gateway.config.models import EmbedMiniBatch
from gateway.embedding.v1 import embedding_pb2, embedding_pb2_grpc
from gateway.providers.provider_registry import get_provider
from gateway.service.embed_mini_batch_service import EmbedMiniBatchService
from gateway.service.request_window_limiter import RequestWindowLimiter
from gateway.util.error_mapping import classify_exception, extract_error_headers
from gateway.util.errors import (
    AppError,
    ErrorKind,
    ErrorMessages,
    TerminalError,
    TransientError,
)
from gateway.util.functions import (
    abort_with_error,
    parse_duration_to_seconds,
)

logger = logging.getLogger(__name__)


class EmbedderService(embedding_pb2_grpc.EmbedderServicer):
    """
    gRPC service for batched embedding requests.

    This service validates requests, splits them into token-safe minibatches,
    executes embedding calls against OpenAI, and returns row-aligned responses.
    """

    # Defaults
    EMBEDDING_PROVIDER = "openai"
    EMBEDDING_MODEL = "text-embedding-3-large"

    # Per-request embedding payload cap.
    MAX_REQUEST_INPUT_TOKENS = 299_000

    # Request-window rate-limit configuration.
    RATE_LIMIT_REQUESTS = 500
    RATE_LIMIT_WINDOW_SECONDS = 0.120

    # Retry configuration for provider rate limiting.
    MAX_RATE_LIMIT_RETRIES = 5

    def __init__(self) -> None:
        # 1) Create the token-aware minibatch builder.
        self._mini_batch_service = EmbedMiniBatchService(
            model_name=self.EMBEDDING_MODEL,
            max_request_tokens=self.MAX_REQUEST_INPUT_TOKENS,
        )

        # 2) Create the rolling request-window limiter used before provider calls.
        self._request_limiter = RequestWindowLimiter(
            max_requests=self.RATE_LIMIT_REQUESTS,
            window_seconds=self.RATE_LIMIT_WINDOW_SECONDS,
        )

    async def EmbedBatch(
        self,
        request: embedding_pb2.EmbedBatchRequest,
        context: grpc.aio.ServicerContext,
    ) -> embedding_pb2.EmbedBatchResponse:  # type: ignore[return-value]
        """
        Embed all valid rows from a batch request.

        Args:
            request: Incoming batch embedding request.
            context: Active gRPC async servicer context.

        Returns:
            EmbedBatchResponse containing row-aligned embedded outputs.

        Raises:
            grpc.RpcError: If validation fails or the RPC is aborted due to
                provider or runtime failures.

        Notes:
            - Rows that exceed the per-request token cap by themselves are dropped
              during minibatch construction.
            - Returned rows preserve the original order of all non-dropped rows.
        """

        # 1) Track end-to-end request duration.
        e2e_start = time.perf_counter()

        # 2) Validate request structure and required row fields.
        await self._validate_request(request=request, context=context)

        # 3) Resolve the OpenAI client used for provider calls.
        client = get_provider(self.EMBEDDING_PROVIDER)

        # 4) Split the request into token-safe minibatches and track oversize rows.
        minibatches, dropped_rows = self._mini_batch_service.build_minibatches(rows=request.rows)

        logger.info(
            "EmbedBatch request: rows=%d minibatches=%d dropped_rows=%d trace_id=%s job_id=%s",
            len(request.rows),
            len(minibatches),
            len(dropped_rows),
            request.trace_id,
            request.job_id,
        )

        # 5) Short-circuit if all rows were dropped during minibatch construction.
        if not minibatches:
            logger.warning(
                "EmbedBatch completed with no valid rows after minibatching: dropped_rows=%d trace_id=%s job_id=%s",
                len(dropped_rows),
                request.trace_id,
                request.job_id,
            )
            return embedding_pb2.EmbedBatchResponse(rows=[])

        try:
            # 6) Execute all minibatches concurrently and preserve output order.
            response_rows = await self.embed_all_minibatches(
                client=client,
                minibatches=minibatches,
                trace_id=request.trace_id,
                job_id=request.job_id,
            )

            # 7) Log final success with counts and total duration.
            logger.info(
                "EmbedBatch finished: model=%s input_rows=%d output_rows=%d dropped_rows=%d trace_id=%s job_id=%s duration=%.3f seconds",
                self.EMBEDDING_MODEL,
                len(request.rows),
                len(response_rows),
                len(dropped_rows),
                request.trace_id,
                request.job_id,
                time.perf_counter() - e2e_start,
            )

            # 8) Return the successful response payload.
            return embedding_pb2.EmbedBatchResponse(rows=response_rows)

        except AppError as ae:
            # 9) Surface known application/provider errors through the shared gateway error contract.
            logger.error(
                "Provider error code=%s kind=%s status=%s trace_id=%s job_id=%s details=%s",
                ae.code,
                ae.kind.value,
                ae.grpc_status.name,
                request.trace_id,
                request.job_id,
                ae.details,
            )
            await abort_with_error(context, ae.grpc_status, ae.code, ae.details)

        except Exception as e:
            # 10) Classify unknown provider/runtime failures when possible.
            try:
                ae = classify_exception(e)
                logger.error(
                    "Provider error code=%s kind=%s status=%s trace_id=%s job_id=%s details=%s",
                    ae.code,
                    ae.kind.value,
                    ae.grpc_status.name,
                    request.trace_id,
                    request.job_id,
                    ae.details,
                )
                await abort_with_error(context, ae.grpc_status, ae.code, ae.details)
            except Exception as e:
                logger.exception(
                    "Unexpected embedding provider failure trace_id=%s job_id=%s",
                    request.trace_id,
                    request.job_id,
                )
                logger.error(e)
                await abort_with_error(
                    context=context,
                    status=grpc.StatusCode.UNAVAILABLE,
                    code=TransientError.NETWORK_ERROR,
                    details=f"{ErrorMessages.NETWORK_ERROR}: {e}",
                )

    async def embed_all_minibatches(
        self,
        *,
        client: AsyncOpenAI,
        minibatches: Sequence[EmbedMiniBatch],
        trace_id: str,
        job_id: str,
    ) -> list[embedding_pb2.EmbedRowResponse]:
        """
        Execute all minibatches concurrently and preserve request order.

        Args:
            client: OpenAI async SDK client.
            minibatches: Token-safe minibatches to embed.
            trace_id: Request trace identifier.
            job_id: Request job identifier.

        Returns:
            Embedded response rows in the same order as the surviving input rows.
        """

        # 1) Launch one task per minibatch.
        tasks = [
            asyncio.create_task(
                self._embed_minibatch_with_retry(
                    client=client,
                    minibatch=minibatch,
                    trace_id=trace_id,
                    job_id=job_id,
                )
            )
            for minibatch in minibatches
        ]

        # 2) Wait for all minibatches to finish.
        results = await asyncio.gather(*tasks)

        # 3) Restore minibatch order because concurrent completion order is arbitrary.
        results.sort(key=lambda item: item[0])

        # 4) Flatten ordered minibatch outputs into one response list.
        ordered_rows: list[embedding_pb2.EmbedRowResponse] = []
        for _, rows in results:
            ordered_rows.extend(rows)

        # 5) Return the ordered rows.
        return ordered_rows

    async def _embed_minibatch_with_retry(
        self,
        *,
        client: AsyncOpenAI,
        minibatch: EmbedMiniBatch,
        trace_id: str,
        job_id: str,
    ) -> tuple[int, list[embedding_pb2.EmbedRowResponse]]:
        """
        Embed one minibatch with retry on provider rate limiting.

        Args:
            client: OpenAI async SDK client.
            minibatch: Minibatch to embed.
            trace_id: Request trace identifier.
            job_id: Request job identifier.

        Returns:
            A tuple of minibatch index and row-aligned embedded responses.

        Raises:
            RateLimitError: If retries are exhausted.
            Exception: If a non-retryable provider failure occurs.
        """

        # 1) Retry the full minibatch when OpenAI returns a rate-limit error.
        last_rate_limit_error: RateLimitError | None = None

        for attempt in range(1, self.MAX_RATE_LIMIT_RETRIES + 1):
            try:
                rows = await self._embed_minibatch(
                    client=client,
                    minibatch=minibatch,
                    trace_id=trace_id,
                    job_id=job_id,
                )
                return minibatch.batch_index, rows

            except RateLimitError as e:
                last_rate_limit_error = e
                sleep_seconds = self._get_rate_limit_sleep_seconds(error=e)

                logger.warning(
                    "Embed minibatch rate limited: batch_index=%d rows=%d tokens=%d attempt=%d sleep=%.3f trace_id=%s job_id=%s",
                    minibatch.batch_index,
                    len(minibatch.rows),
                    minibatch.total_tokens,
                    attempt,
                    sleep_seconds,
                    trace_id,
                    job_id,
                )

                await asyncio.sleep(sleep_seconds)

        # 2) Raise the last observed rate-limit error after retry exhaustion.
        assert last_rate_limit_error is not None
        raise last_rate_limit_error

    async def _embed_minibatch(
        self,
        *,
        client: AsyncOpenAI,
        minibatch: EmbedMiniBatch,
        trace_id: str,
        job_id: str,
    ) -> list[embedding_pb2.EmbedRowResponse]:
        """
        Embed one minibatch and construct row-aligned response records.

        Args:
            client: OpenAI async SDK client.
            minibatch: Minibatch to embed.
            trace_id: Request trace identifier.
            job_id: Request job identifier.

        Returns:
            Row-aligned embedded responses for the minibatch.

        Raises:
            AppError: If provider output cardinality does not match input rows.
            Exception: If provider calls fail.
        """

        # 1) Preserve row order by extracting text fields in minibatch order.
        student_texts = [row.student_answer_text for row in minibatch.rows]
        feedback_texts = [row.feedback_text for row in minibatch.rows]

        # 2) Track provider duration for this minibatch.
        model_start = time.perf_counter()

        # 3) Create embeddings for student answer texts.
        embed_args = {
            "client": client,
            "trace_id": trace_id,
            "job_id": job_id,
            "batch_index": minibatch.batch_index,
        }
        student_response = await self._create_embeddings_with_retry(
            **embed_args,
            label="student",
            texts=student_texts,
        )

        # 4) Create embeddings for feedback texts.
        feedback_response = await self._create_embeddings_with_retry(
            **embed_args,
            label="feedback",
            texts=feedback_texts,
        )

        # 5) Defensively verify output cardinality before reconstructing rows.
        if (len(student_response.data) != len(minibatch.rows)) or (
            len(feedback_response.data) != len(minibatch.rows)
        ):
            causes = []
            if len(student_response.data) != len(minibatch.rows):
                causes.append("student_response")
            if len(feedback_response.data) != len(minibatch.rows):
                causes.append("feedback_response")
            raise AppError(
                code=TransientError.SCHEMA_MISMATCH,
                kind=ErrorKind.TRANSIENT,
                grpc_status=grpc.StatusCode.UNAVAILABLE,
                details="Embedding response size mismatch.",
                cause=" | ".join(causes),
            )

        # 6) Reconstruct row-aligned proto responses in original minibatch order.
        response_rows: list[embedding_pb2.EmbedRowResponse] = []
        for idx, row in enumerate(minibatch.rows):
            response_rows.append(
                embedding_pb2.EmbedRowResponse(
                    workup_id=row.workup_id,
                    submission_id=row.submission_id,
                    disease_id=row.disease_id,
                    section_type=row.section_type,
                    student_answer_text=row.student_answer_text,
                    student_answer_vector=student_response.data[idx].embedding,
                    feedback_text=row.feedback_text,
                    feedback_vector=feedback_response.data[idx].embedding,
                    embedding_model=self.EMBEDDING_MODEL,
                )
            )

        # 7) Log minibatch success with stable identifiers and duration.
        logger.info(
            "Embed minibatch success: batch_index=%d rows=%d tokens=%d model=%s trace_id=%s job_id=%s duration=%.3f seconds",
            minibatch.batch_index,
            len(minibatch.rows),
            minibatch.total_tokens,
            self.EMBEDDING_MODEL,
            trace_id,
            job_id,
            time.perf_counter() - model_start,
        )

        # 8) Return minibatch rows.
        return response_rows

    async def _create_embeddings_with_retry(
        self,
        *,
        client: AsyncOpenAI,
        texts: Sequence[str],
        label: str,
        trace_id: str,
        job_id: str,
        batch_index: int,
    ):
        """
        Call the OpenAI embeddings API with rate-limit-aware retry.

        Args:
            client: OpenAI async SDK client.
            texts: Text inputs to embed.
            label: Logical label used only for logging.
            trace_id: Request trace identifier.
            job_id: Request job identifier.
            batch_index: Minibatch index for observability.

        Returns:
            OpenAI embedding response object.

        Raises:
            RateLimitError: If retries are exhausted.
            Exception: If a non-rate-limit error occurs.
        """

        # 1) Retry the provider call on rate limiting.
        last_rate_limit_error: RateLimitError | None = None

        for attempt in range(1, self.MAX_RATE_LIMIT_RETRIES + 1):
            try:
                # 2) Respect the rolling request-window limiter before the call.
                await self._request_limiter.acquire()

                # 3) Call the OpenAI embeddings API.
                return await client.embeddings.create(
                    model=self.EMBEDDING_MODEL,
                    input=list(texts),
                )

            except RateLimitError as e:
                last_rate_limit_error = e
                sleep_seconds = self._get_rate_limit_sleep_seconds(error=e)

                logger.warning(
                    "Embedding call rate limited: batch_index=%d label=%s inputs=%d attempt=%d sleep=%.3f trace_id=%s job_id=%s",
                    batch_index,
                    label,
                    len(texts),
                    attempt,
                    sleep_seconds,
                    trace_id,
                    job_id,
                )

                await asyncio.sleep(sleep_seconds)

        # 4) Raise the last observed rate-limit error after retry exhaustion.
        assert last_rate_limit_error is not None
        raise last_rate_limit_error

    @staticmethod
    async def _validate_request(
        request: embedding_pb2.EmbedBatchRequest,
        context: grpc.aio.ServicerContext,
    ) -> None:
        """
        Validate the top-level embedding request and each row payload.

        Args:
            request: Incoming batch embedding request.
            context: Active gRPC async servicer context.

        Raises:
            grpc.RpcError: If validation fails and the RPC is aborted.
        """

        args = {
            "context": context,
            "status": grpc.StatusCode.INVALID_ARGUMENT,
            "code": TerminalError.INVALID_PAYLOAD,
        }

        # 1) Require at least one row.
        if not request.rows:
            await abort_with_error(
                **args,
                details="EmbedBatch requires at least one row.",
            )

        # 2) Validate required fields for each row.
        for idx, row in enumerate(request.rows):
            if not row.submission_id.strip():
                await abort_with_error(
                    **args,
                    details=f"rows[{idx}].submission_id is required.",
                )

            if not row.disease_id.strip():
                await abort_with_error(
                    **args,
                    details=f"rows[{idx}].disease_id is required.",
                )

            if not row.section_type.strip():
                await abort_with_error(
                    **args,
                    details=f"rows[{idx}].section_type is required.",
                )

            if not row.student_answer_text.strip():
                await abort_with_error(
                    **args,
                    details=f"rows[{idx}].student_answer_text is required.",
                )

            if not row.feedback_text.strip():
                await abort_with_error(
                    **args,
                    details=f"rows[{idx}].feedback_text is required.",
                )

    @staticmethod
    def _get_rate_limit_sleep_seconds(
        *,
        error: RateLimitError,
        fallback_sleep_seconds: float = 0.120,
    ) -> float:
        """
        Extract retry sleep duration from an OpenAI rate-limit exception.

        Supported header formats:
            - retry-after, x-ratelimit-reset-requests

        Supported duration examples:
            - "120ms", "2s", "1m", "0.5", "3"

        Args:
            error: OpenAI rate-limit exception.
            fallback_sleep_seconds: Fallback sleep duration when no usable header
                value is present.

        Returns:
            Sleep duration in seconds.
        """

        # 1) Extract normalized response headers from the exception.
        headers = extract_error_headers(error=error)  # type: ignore

        # 2) Prefer retry-after when present.
        retry_after = headers.get("retry-after")
        if retry_after:
            parsed = parse_duration_to_seconds(value=retry_after)
            if parsed is not None:
                return parsed

        # 3) Fall back to x-ratelimit-reset-requests when present.
        reset_requests = headers.get("x-ratelimit-reset-requests")
        if reset_requests:
            parsed = parse_duration_to_seconds(value=reset_requests)
            if parsed is not None:
                return parsed

        # 4) Fall back to the configured default.
        return fallback_sleep_seconds
