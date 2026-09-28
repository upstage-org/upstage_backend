### Application API Endpoints

- Endpoint: `POST <host>/api/studio_graphql` (HTTP only; there is no GraphQL WebSocket route and the schema has no `Subscription` type).
- The schema (SDL) is the `type_defs` string in `src/upstage_backend/studio_management/http/graphql.py`. That file is the authoritative reference for every type, input and enum; this document lists the operations, who may call them, and an example request for each. The examples below are validated against that SDL.
- Resolvers are in each module's `http/schema.py` and are bound to the schema in `config_graphql_endpoints` (`src/upstage_backend/global_config/schema.py`).

The only other HTTP route is `POST /api/rtmp/auth` (`src/upstage_backend/assets/http/rtmp_auth.py`), which is called by the MediaMTX streaming server, not by API clients.

### Authentication

- `login` returns `access_token` and `refresh_token` (JWTs).
- Authenticated operations need the header `Authorization: Bearer <access_token>`.
- `refreshToken` reads the refresh token from the header `X-Access-Token`.
- `logout` reads the access token from the `Authorization` header.

Roles (`src/upstage_backend/users/db_models/user.py`): Player = `1`, Guest = `4`, Admin = `8`, Super admin = `32`.

The "Access" line of each operation below is what the resolver's `@authenticated(allowed_roles=...)` decorator enforces:

| Access | Meaning |
|---|---|
| Public | No decorator; no token needed |
| Any logged-in user | `@authenticated()` with no role list |
| Player, Admin, Super admin | `allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER]` |
| Admin, Super admin | `allowed_roles=[SUPER_ADMIN, ADMIN]` |

Services may apply further checks (ownership, stage permission) on top of the decorator; those noted below are the ones stated in the code that was read for this document, not a complete list.

Authentication failures are GraphQL errors with one of these messages: `Authenticated Failed`, `Signature has expired`, `Permission denied`.

### Common Error Response Structure

In case of an error, the API returns the standard GraphQL error structure:

```json
{
    "data": {
        "operationName": null
    },
    "errors": [
        {
            "message": "Error message describing the issue.",
            "locations": [
                {
                    "line": 2,
                    "column": 3
                }
            ],
            "path": [
                "operationName"
            ]
        }
    ]
}
```

Example Error Response:

```json
{
    "data": {
        "login": null
    },
    "errors": [
        {
            "message": "Incorrect username or password. Please try again.",
            "locations": [
                {
                    "line": 2,
                    "column": 3
                }
            ],
            "path": [
                "login"
            ]
        }
    ]
}
```

A request that fails validation against the schema has no `data` key and its errors have no `path`. When `ENV_TYPE` is neither `"Production"` nor `"Dev"`, the GraphQL app runs in debug mode and errors carry additional debug information.

Timestamps serialised from the database models carry the UTC offset, for example `2024-11-26T17:42:04.545183+00:00`.

---

## Users and authentication

**login**

`login(payload: LoginInput!): TokenType` — Access: Public. `LoginInput.token` is the captcha token, verified only when `ENV_TYPE` is `"Production"`.

```graphql
mutation {
    login(payload: {
        username: "user123",
        password: "password123"
    }) {
        user_id
        access_token
        refresh_token
        role
        first_name
        groups {
            id
            name
        }
        username
        title
    }
}
```

**refreshToken**

`refreshToken: RefreshTokenResponse` — Access: Public (needs a valid refresh token in the `X-Access-Token` header).

```graphql
mutation {
    refreshToken {
        access_token
        refresh_token
    }
}
```

**logout**

`logout: String` — Access: Public (needs the access token in the `Authorization` header). Returns `"Logged out"`.

```graphql
mutation {
    logout
}
```

**currentUser**

`currentUser: User` — Access: Any logged-in user.

```graphql
query {
    currentUser {
        id
        username
        email
        effectiveUploadLimit
    }
}
```

**whoami**

`whoami: User` — Access: Any logged-in user. Also fills `roleName`.

```graphql
query {
    whoami {
        id
        username
        email
        roleName
        effectiveUploadLimit
    }
}
```

**createUser**

`createUser(inbound: CreateUserInput!): CreateUserPayload` — Access: Public. The resolver validates the input further (`users/http/validation.py`): `email` and `intro` are required, `password` has a minimum length of 8, `username` a minimum length of 2.

```graphql
mutation {
    createUser(inbound: {
        username: "janedoe",
        password: "password123",
        email: "jane.doe@example.com",
        intro: "Hello"
    }) {
        user {
            id
            username
            email
        }
    }
}
```

**requestPasswordReset**

`requestPasswordReset(email: String!): CommonResponse` — Access: Public.

```graphql
mutation {
    requestPasswordReset(email: "jane.doe@example.com") {
        success
        message
    }
}
```

**verifyPasswordReset**

`verifyPasswordReset(input: ResetPasswordInput!): CommonResponse` — Access: Public. Uses `email` and `token` of the input.

```graphql
mutation {
    verifyPasswordReset(input: {
        email: "jane.doe@example.com",
        token: "123456"
    }) {
        success
        message
    }
}
```

**resetPassword**

`resetPassword(input: ResetPasswordInput!): CommonResponse` — Access: Public. `password` is nullable in the SDL but required by the resolver's validation (minimum length 8).

```graphql
mutation {
    resetPassword(input: {
        email: "jane.doe@example.com",
        token: "123456",
        password: "newPassword123"
    }) {
        success
        message
    }
}
```

**changePassword**

`changePassword(input: ChangePasswordInput!): CommonResponse` — Access: Any logged-in user.

```graphql
mutation {
    changePassword(input: {
        oldPassword: "oldPassword123",
        newPassword: "newPassword123",
        id: "1"
    }) {
        success
        message
    }
}
```

## Studio: user administration

**users**

`users(active: Boolean): [User!]!` — Access: Player, Admin, Super admin. For callers who are not admins the service trims the result to the public user fields.

```graphql
query {
    users(active: true) {
        id
        username
        displayName
    }
}
```

**adminPlayers**

`adminPlayers(limit: Int, page: Int, sort: [AdminPlayerSortEnum], usernameLike: String, createdBetween: [String]): AdminPlayerConnection` — Access: Any logged-in user. For callers who are not admins the service trims the result to the public user fields.

```graphql
query {
    adminPlayers(limit: 10, page: 1, sort: [USERNAME_ASC]) {
        totalCount
        edges {
            id
            username
            displayName
        }
    }
}
```

**batchUserCreation**

`batchUserCreation(users: [BatchUserInput]!): BatchUserCreationPayload` — Access: Admin, Super admin.

```graphql
mutation {
    batchUserCreation(users: [
        {
            username: "user1",
            password: "password1",
            email: "user1@example.com"
        },
        {
            username: "user2",
            password: "password2",
            email: "user2@example.com"
        }
    ]) {
        users {
            id
            username
            email
        }
    }
}
```

**updateUser**

`updateUser(input: UpdateUserInput!): User` — Access: Player, Admin, Super admin.

```graphql
mutation {
    updateUser(input: {
        id: "1",
        username: "updatedUser",
        email: "updated@example.com"
    }) {
        id
        username
        email
    }
}
```

**deleteUser**

`deleteUser(id: ID!, contentAction: UserContentAction = REASSIGN_TO_ADMIN): CommonResponse` — Access: Admin, Super admin. `contentAction` is `REASSIGN_TO_ADMIN` or `DELETE_ALL`.

```graphql
mutation {
    deleteUser(id: "1", contentAction: REASSIGN_TO_ADMIN) {
        success
        message
    }
}
```

**sendEmail**

`sendEmail(input: SendEmailInput!): CommonResponse` — Access: Any logged-in user; the resolver then requires the caller to be an Admin / Super admin or to have `canSendEmail` set. `recipients` and `bcc` are comma-separated; at least one address is required. Returns `success: true`.

```graphql
mutation {
    sendEmail(input: {
        subject: "Test Email",
        body: "This is a test email.",
        recipients: "recipient@example.com",
        bcc: "bcc@example.com"
    }) {
        success
        message
    }
}
```

**calcSizes**

`calcSizes: Size` — Access: Admin, Super admin.

```graphql
mutation {
    calcSizes {
        size
    }
}
```

## Stages

**stages**

`stages(input: SearchStageInput): StagesResponse` — Access: Player, Admin, Super admin.

```graphql
query {
    stages(input: { page: 1, limit: 10, sort: [NAME_ASC] }) {
        totalCount
        edges {
            id
            name
            fileLocation
            status
            visibility
            cover
            description
            playerAccess
            permission
            owner {
                username
            }
            assets {
                id
                name
            }
        }
    }
}
```

**stage**

`stage(id: ID!): Stage` — Access: Player, Admin, Super admin.

```graphql
query {
    stage(id: "1") {
        id
        name
        description
        visibility
        createdOn
        lastAccess
    }
}
```

**getAllStages**

`getAllStages: [Stage!]!` — Access: Any logged-in user.

```graphql
query {
    getAllStages {
        id
        name
        owner {
            username
            displayName
        }
        createdOn
    }
}
```

**foyerStageList**

`foyerStageList: [Stage!]!` — Access: Public.

```graphql
query {
    foyerStageList {
        id
        name
        owner {
            displayName
            username
        }
        fileLocation
        cover
    }
}
```

**stageList**

`stageList(input: StageStreamInput): [Stage!]!` — Access: Public. A bearer token, when sent, identifies the caller. `StageStreamInput` takes `fileLocation`, `performanceId` (replay an archived performance) and `cursor` (only events with a greater id). `mqtt` returns the broker login the browser connects with.

```graphql
query {
    stageList(input: { fileLocation: "duplicate-stage17" }) {
        id
        name
        fileLocation
        owner {
            id
            binName
            username
        }
        attributes {
            id
            name
            description
        }
        visibility
        status
        permission
        assets {
            assetType {
                name
            }
            name
            id
            fileLocation
            description
        }
        scenes {
            id
            name
        }
        events {
            id
            topic
            payload
            mqttTimestamp
        }
        mqtt {
            username
            password
        }
    }
}
```

**notifications**

`notifications: [Notification]` — Access: Player, Admin, Super admin. `type` is `1` (media usage request), `2` (permission approved) or `3` (media acknowledgement).

```graphql
query {
    notifications {
        type
        mediaUsage {
            id
            assetId
            userId
            approved
            note
            createdOn
        }
    }
}
```

**createStage**

`createStage(input: StageInput!): Stage` — Access: Player, Admin, Super admin. `fileLocation` is the stage's URL slug: letters, digits, `-` and `_`, and unique.

```graphql
mutation {
    createStage(input: {
        name: "New Stage",
        fileLocation: "new-stage",
        description: "Stage description",
        visibility: true
    }) {
        id
        name
        fileLocation
        description
        visibility
    }
}
```

**updateStage**

`updateStage(input: StageInput!): Stage` — Access: Player, Admin, Super admin.

```graphql
mutation {
    updateStage(input: {
        id: "1",
        name: "Updated Stage",
        description: "Updated description"
    }) {
        id
        name
        description
    }
}
```

**duplicateStage**

`duplicateStage(id: ID!, name: String!): Stage` — Access: Player, Admin, Super admin.

```graphql
mutation {
    duplicateStage(id: "1", name: "Duplicate Stage") {
        id
        name
        description
    }
}
```

**deleteStage**

`deleteStage(id: ID!): CommonResponse` — Access: Player, Admin, Super admin.

```graphql
mutation {
    deleteStage(id: "1") {
        success
        message
    }
}
```

**sweepStage**

`sweepStage(id: ID!): SweepResponse` — Access: Player, Admin, Super admin; the service then requires the caller to be the stage owner, an admin, or an editor of the stage. Fails with "The stage is already sweeped!" when there are no live events.

```graphql
mutation {
    sweepStage(id: "1") {
        success
        performanceId
    }
}
```

**updateStatus**

`updateStatus(id: ID!): UpdateStageResponse` — Access: Player, Admin, Super admin.

```graphql
mutation {
    updateStatus(id: "1") {
        result
    }
}
```

**updateVisibility**

`updateVisibility(id: ID!): UpdateStageResponse` — Access: Player, Admin, Super admin.

```graphql
mutation {
    updateVisibility(id: "1") {
        result
    }
}
```

**updateLastAccess**

`updateLastAccess(id: ID!): UpdateStageResponse` — Access: Public.

```graphql
mutation {
    updateLastAccess(id: "1") {
        result
    }
}
```

## Scenes, performances and recordings

**saveScene**

`saveScene(input: SceneInput!): Scene` — Access: Any logged-in user.

```graphql
mutation {
    saveScene(input: {
        name: "New Scene",
        stageId: "1",
        payload: "{}"
    }) {
        id
        name
        stageId
    }
}
```

**deleteScene**

`deleteScene(id: ID!): CommonResponse` — Access: Player, Admin, Super admin.

```graphql
mutation {
    deleteScene(id: "1") {
        success
        message
    }
}
```

**updatePerformance**

`updatePerformance(input: PerformanceInput!): CommonResponse` — Access: Player, Admin, Super admin.

```graphql
mutation {
    updatePerformance(input: {
        id: "1",
        name: "Updated Performance"
    }) {
        success
        message
    }
}
```

**deletePerformance**

`deletePerformance(id: ID!): CommonResponse` — Access: Player, Admin, Super admin.

```graphql
mutation {
    deletePerformance(id: "1") {
        success
        message
    }
}
```

**duplicatePerformanceWithTrimmedPauses**

`duplicatePerformanceWithTrimmedPauses(input: DuplicatePerformanceTrimInput!): Performance` — Access: Player, Admin, Super admin.

```graphql
mutation {
    duplicatePerformanceWithTrimmedPauses(input: {
        sourcePerformanceId: "1",
        name: "Trimmed copy",
        minPauseSeconds: 5
    }) {
        id
        name
        stageId
    }
}
```

**startRecording**

`startRecording(input: RecordInput!): Performance` — Access: Player, Admin, Super admin; the service then requires the caller to be the stage owner or an admin.

```graphql
mutation {
    startRecording(input: {
        stageId: "1",
        name: "New Recording"
    }) {
        id
        name
        stageId
        recording
    }
}
```

**saveRecording**

`saveRecording(id: ID!): Performance` — Access: Player, Admin, Super admin; the service then requires the caller to be the stage owner or an admin. Fails with "Nothing to record!" when no events were archived since the recording started.

```graphql
mutation {
    saveRecording(id: "1") {
        id
        name
        stageId
        savedOn
    }
}
```

**performanceCommunication**

`performanceCommunication: [PerformanceCommunication!]!` — Access: Admin, Super admin.

```graphql
query {
    performanceCommunication {
        id
        ownerId
        ipAddress
        websocketPort
        webclientPort
        topicName
        username
        password
        createdOn
        expiresOn
        performanceConfigId
    }
}
```

**performanceConfig**

`performanceConfig: [PerformanceConfig!]!` — Access: Admin, Super admin.

```graphql
query {
    performanceConfig {
        id
        name
        ownerId
        description
        splashScreenText
        splashScreenAnimationUrls
        createdOn
        expiresOn
    }
}
```

**scene**

`scene: [Scene!]!` — Access: Admin, Super admin.

```graphql
query {
    scene {
        id
        name
        sceneOrder
        scenePreview
        payload
        createdOn
        active
        ownerId
        stageId
    }
}
```

**parentStage**

`parentStage: [ParentStage!]` — Access: Admin, Super admin.

```graphql
query {
    parentStage {
        id
        stageId
        childAssetId
        exitAnimation
        exitSpeed
        stage {
            id
            name
        }
        childAsset {
            id
            name
        }
    }
}
```

## Media

**media**

`media(input: MediaTableInput!): AssetConnection!` — Access: Player, Admin, Super admin.

```graphql
query {
    media(input: { page: 1, limit: 10 }) {
        totalCount
        edges {
            id
            name
            src
        }
    }
}
```

**mediaList**

`mediaList(mediaType: String, owner: String): [Asset!]!` — Access: Player, Admin, Super admin.

```graphql
query {
    mediaList(mediaType: "image", owner: "owner1") {
        id
        name
        src
    }
}
```

**mediaTypes**

`mediaTypes: [AssetType!]!` — Access: Player, Admin, Super admin.

```graphql
query {
    mediaTypes {
        id
        name
    }
}
```

**tags**

`tags: [Tag!]!` — Access: Player, Admin, Super admin.

```graphql
query {
    tags {
        id
        name
        color
        createdOn
    }
}
```

**voices**

`voices: [Voice!]` — Access: Player, Admin, Super admin.

```graphql
query {
    voices {
        avatar {
            id
            name
        }
        voice {
            voice
            variant
            pitch
            speed
            amplitude
        }
    }
}
```

**uploadFile**

`uploadFile(base64: String!, filename: String!): File!` — Access: Player, Admin, Super admin.

```graphql
mutation {
    uploadFile(base64: "base64string", filename: "file.png") {
        url
    }
}
```

**saveMedia**

`saveMedia(input: SaveMediaInput!): SaveMediaPayload!` — Access: Player, Admin, Super admin.

```graphql
mutation {
    saveMedia(input: {
        name: "New Media",
        mediaType: "image",
        copyrightLevel: 1,
        owner: "owner1",
        stageAssignments: [{ stageId: "1" }],
        tags: ["tag1", "tag2"],
        w: 1920,
        h: 1080,
        urls: ["image/media.png"]
    }) {
        asset {
            id
            name
            src
        }
    }
}
```

**uploadMedia**

`uploadMedia(input: UploadMediaInput!): Asset` — Access: Player, Admin, Super admin.

```graphql
mutation {
    uploadMedia(input: {
        name: "New Media",
        base64: "base64string",
        mediaType: "image",
        filename: "media.png"
    }) {
        id
        name
        src
    }
}
```

**updateMedia**

`updateMedia(input: UpdateMediaInput!): Asset` — Access: Player, Admin, Super admin.

```graphql
mutation {
    updateMedia(input: {
        id: "1",
        name: "Updated Media",
        description: "Updated description"
    }) {
        id
        name
        description
    }
}
```

**updateMediaStatus**

`updateMediaStatus(input: UpdateMediaStatusInput): CommonResponse` — Access: Player, Admin, Super admin. `status` is `Active`, `Dormant` or `Remove`.

```graphql
mutation {
    updateMediaStatus(input: {
        id: "64",
        status: Dormant
    }) {
        message
        success
    }
}
```

**deleteMedia**

`deleteMedia(id: ID!): DeleteMediaPayload!` — Access: Player, Admin, Super admin.

```graphql
mutation {
    deleteMedia(id: "1") {
        success
        message
    }
}
```

**deleteMediaOnStage**

`deleteMediaOnStage(id: ID!): CommonResponse` — Access: Player, Admin, Super admin.

```graphql
mutation {
    deleteMediaOnStage(id: "1") {
        success
        message
    }
}
```

**assignMedia**

`assignMedia(input: AssignMediaInput!): Stage` — Access: Player, Admin, Super admin. `id` is the stage id.

```graphql
mutation {
    assignMedia(input: {
        id: "1",
        mediaIds: ["1", "2"]
    }) {
        id
        name
    }
}
```

**assignStages**

`assignStages(input: AssignStagesInput!): Asset` — Access: Player, Admin, Super admin. `id` is the asset id.

```graphql
mutation {
    assignStages(input: {
        id: "1",
        stageIds: ["1", "2"]
    }) {
        id
        name
    }
}
```

**updateStageAssignment**

`updateStageAssignment(stageId: ID!, assetId: ID!, exitAnimation: String, exitSpeed: Int): ParentStage` — Access: Player, Admin, Super admin.

```graphql
mutation {
    updateStageAssignment(stageId: "1", assetId: "1", exitAnimation: "fade", exitSpeed: 2) {
        id
        stageId
        childAssetId
        exitAnimation
        exitSpeed
    }
}
```

**quickAssignMutation**

`quickAssignMutation(stageIds: [ID]!, assetId: ID!): CommonResponse` — Access: Any logged-in user.

```graphql
mutation {
    quickAssignMutation(stageIds: ["1"], assetId: "1") {
        success
        message
    }
}
```

## Media permissions

**requestPermission**

`requestPermission(assetId: ID!, note: String): ConfirmPermissionResponse` — Access: Any logged-in user.

```graphql
mutation {
    requestPermission(assetId: "1", note: "Requesting permission") {
        success
        message
        permissions {
            id
            userId
            assetId
            approved
            createdOn
            note
            user {
                username
                displayName
            }
        }
    }
}
```

**confirmPermission**

`confirmPermission(id: ID!, approved: Boolean): ConfirmPermissionResponse` — Access: Any logged-in user.

```graphql
mutation {
    confirmPermission(id: "1", approved: true) {
        success
        message
        permissions {
            id
            userId
            assetId
            approved
            createdOn
            note
            user {
                username
                displayName
            }
        }
    }
}
```

**dismissNotification**

`dismissNotification(id: ID!): AssetUsage` — Access: Player, Admin, Super admin.

```graphql
mutation {
    dismissNotification(id: "1") {
        id
        ownerSeen
        requesterSeen
    }
}
```

## Licenses

**createLicense**

`createLicense(input: LicenseInput!): License!` — Access: Admin, Super admin.

```graphql
mutation {
    createLicense(input: {
        assetId: "123",
        level: 1,
        permissions: "read"
    }) {
        id
        assetId
        createdOn
        level
        permissions
        assetPath
    }
}
```

**revokeLicense**

`revokeLicense(id: ID!): String!` — Access: Admin, Super admin.

```graphql
mutation {
    revokeLicense(id: "1")
}
```

## Site configuration

**nginx**

`nginx: NginxConfig!` — Access: Public.

```graphql
query {
    nginx {
        limit
    }
}
```

**system**

`system: SystemConfig!` — Access: Public.

```graphql
query {
    system {
        termsOfService {
            id
            name
            value
            createdOn
        }
        manual {
            id
            name
            value
            createdOn
        }
        esp {
            id
            name
            value
            createdOn
        }
        enableDonate {
            id
            name
            value
            createdOn
        }
        emailSignature {
            id
            name
            value
            createdOn
        }
        addingEmailSignature {
            id
            name
            value
            createdOn
        }
    }
}
```

**foyer**

`foyer: FoyerConfig!` — Access: Public.

```graphql
query {
    foyer {
        title {
            id
            name
            value
            createdOn
        }
        description {
            id
            name
            value
            createdOn
        }
        menu {
            id
            name
            value
            createdOn
        }
        showRegistration {
            id
            name
            value
            createdOn
        }
    }
}
```

**updateTermsOfService**

`updateTermsOfService(url: String!): Config` — Access: Admin, Super admin.

```graphql
mutation {
    updateTermsOfService(url: "http://example.com/new-tos") {
        id
        name
        value
        createdOn
    }
}
```

**saveConfig**

`saveConfig(input: ConfigInput!): Config` — Access: Admin, Super admin.

```graphql
mutation {
    saveConfig(input: {
        name: "New Config",
        value: "Config Value"
    }) {
        id
        name
        value
        createdOn
    }
}
```

**sendSystemEmail**

`sendSystemEmail(input: SystemEmailInput!): CommonResponse` — Access: Admin, Super admin.

```graphql
mutation {
    sendSystemEmail(input: {
        subject: "Notice",
        body: "This is a system email.",
        recipients: "recipient@example.com"
    }) {
        success
        message
    }
}
```

## Payments

**paymentSecret**

`paymentSecret(input: PaymentIntentInput!): String!` — Access: Public (anonymous donations). `token` is the captcha token, verified only when `ENV_TYPE` is `"Production"`.

```graphql
mutation {
    paymentSecret(input: {
        amount: 1000,
        currency: "usd"
    })
}
```

**generateReceipt**

`generateReceipt(receivedFrom: String!, description: String!, amount: String!, date: String!): ReceiptFile!` — Access: Public.

```graphql
mutation {
    generateReceipt(
        receivedFrom: "Jane Doe",
        description: "Donation",
        amount: "10.00",
        date: "2026-01-31"
    ) {
        fileBase64
        fileName
    }
}
```

**oneTimeDonation**, **createSubscription**, **cancelSubscription**, **updateEmailCustomer**

Access: Admin, Super admin. Per the comment in `src/upstage_backend/payments/http/schema.py`, these four mutations are not used by the studio UI (the donate flow uses `paymentSecret`) and are restricted to admins until they are removed or redesigned.

- `oneTimeDonation(input: OneTimeDonationInput!): CommonResponse`
- `createSubscription(input: CreateSubscriptionInput!): CommonResponse`
- `cancelSubscription(subscription_id: String!): CommonResponse`
- `updateEmailCustomer(customer_id: String!, email: String!): CommonResponse`

```graphql
mutation {
    cancelSubscription(subscription_id: "sub_12345") {
        success
        message
    }
}
```

```graphql
mutation {
    updateEmailCustomer(customer_id: "cus_12345", email: "new.email@example.com") {
        success
        message
    }
}
```
