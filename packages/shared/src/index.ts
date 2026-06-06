export type ProfileId = string;

export interface ProfileScope {
  userId: string;
  profileId: ProfileId;
}

export interface HealthResponse {
  status: "ok";
}

export const createScopedKey = (
  scope: ProfileScope,
  suffix: string,
): string => {
  return `${scope.userId}:${scope.profileId}:${suffix}`;
};
