import { useMutation, useQueryClient, type UseMutationResult } from "@tanstack/react-query";

import {
  getCurrentUserQueryKey,
  updateCurrentUserMutation,
  type CurrentUserResponse,
  type Options,
  type UpdateCurrentUserData,
  type UpdateCurrentUserError,
} from "../../api/sdk";
import { isSessionInvalid } from "../../user/sessionInvalid";

export type ProfileUpdate = UseMutationResult<
  CurrentUserResponse,
  UpdateCurrentUserError,
  Options<UpdateCurrentUserData>
>;

/**
 * PATCH of the profile. The response is the whole profile, so it replaces the cached `/me` and the
 * greeting and header follow without a second request. A gone account refetches `/me`: the
 * current-user provider then sees the same code and logs out.
 */
export function useProfileUpdate(): ProfileUpdate {
  const queryClient = useQueryClient();

  return useMutation({
    ...updateCurrentUserMutation(),
    onSuccess: (profile) => {
      queryClient.setQueryData(getCurrentUserQueryKey(), profile);
    },
    onError: (error) => {
      if (isSessionInvalid(error)) {
        void queryClient.invalidateQueries({ queryKey: getCurrentUserQueryKey() });
      }
    },
  });
}
