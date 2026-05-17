import { useCallback, useEffect, useMemo } from "react";
import { useConversationStore } from "#/stores/conversation-store";
import { useActiveConversation } from "#/hooks/query/use-active-conversation";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";
import { useSubConversations } from "#/hooks/query/use-sub-conversations";
import { useSettings } from "#/hooks/query/use-settings";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import {
  getConversationState,
  setConversationState,
} from "#/utils/conversation-local-storage";

const WORKFLOW_REVIEW_PHASE = "review";

export const useHandleReviewClick = () => {
  const {
    setConversationMode,
    setSubConversationTaskId,
    subConversationTaskId,
  } = useConversationStore();
  const { data: conversation } = useActiveConversation();
  const { data: settings } = useSettings();
  const { data: subConversations } = useSubConversations(
    conversation?.sub_conversation_ids ?? [],
  );
  const { mutate: createConversation, isPending: isCreatingConversation } =
    useCreateConversation();

  useEffect(() => {
    if (!conversation?.id) return;
    const storedState = getConversationState(conversation.id);
    if (storedState.subConversationTaskId && !subConversationTaskId) {
      setSubConversationTaskId(storedState.subConversationTaskId);
    }
  }, [conversation?.id, subConversationTaskId, setSubConversationTaskId]);

  const reviewIterationsUsed = useMemo(
    () =>
      (subConversations ?? []).filter(
        (subConversation) =>
          subConversation?.tags?.workflow_phase === WORKFLOW_REVIEW_PHASE,
      ).length,
    [subConversations],
  );

  const maxReviewIterations =
    settings?.workflow_settings?.max_review_iterations ?? 3;

  const handleReviewClick = useCallback(
    (event?: React.MouseEvent<HTMLButtonElement> | KeyboardEvent) => {
      event?.preventDefault();
      event?.stopPropagation();
      setConversationMode("review");

      if (!conversation?.id || subConversationTaskId) {
        return;
      }

      const nextIteration = reviewIterationsUsed + 1;
      if (nextIteration > maxReviewIterations) {
        displayErrorToast(
          `Review loop limit reached (${maxReviewIterations} iterations).`,
        );
        return;
      }

      createConversation(
        {
          parentConversationId: conversation.id,
          agentType: "default",
          workflowPhase: "review",
          workflowIteration: nextIteration,
        },
        {
          onSuccess: (data) => {
            displaySuccessToast(
              `Review iteration ${nextIteration} initialized.`,
            );
            if (data.v1_task_id) {
              setSubConversationTaskId(data.v1_task_id);
              setConversationState(conversation.id, {
                subConversationTaskId: data.v1_task_id,
              });
            }
          },
        },
      );
    },
    [
      setConversationMode,
      conversation?.id,
      subConversationTaskId,
      reviewIterationsUsed,
      maxReviewIterations,
      createConversation,
      setSubConversationTaskId,
    ],
  );

  return { handleReviewClick, isCreatingConversation };
};
