import { AuthConfig, CognitoUserPoolConfig } from '@aws-amplify/core';

// AWS Amplify configuration — all Cognito values read from environment variables
// See frontend/README.md for required environment variables
const getCognitoConfig = (): CognitoUserPoolConfig => {
	const domain = process.env.NEXT_PUBLIC_COGNITO_DOMAIN;
	const userPoolId = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID;
	const clientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID;
	const region = process.env.NEXT_PUBLIC_COGNITO_REGION ?? 'us-east-1';
	const redirectSignIn = process.env.NEXT_PUBLIC_COGNITO_REDIRECT_SIGN_IN ?? "http://localhost:3000/";
	const redirectSignOut = process.env.NEXT_PUBLIC_COGNITO_REDIRECT_SIGN_OUT ?? "http://localhost:3000/";

	// Log warning if required variables are missing
	if (!domain || !userPoolId || !clientId) {
		console.warn(
			'⚠️ Missing Cognito environment variables:\n' +
			(domain ? '' : '  - NEXT_PUBLIC_COGNITO_DOMAIN\n') +
			(userPoolId ? '' : '  - NEXT_PUBLIC_COGNITO_USER_POOL_ID\n') +
			(clientId ? '' : '  - NEXT_PUBLIC_COGNITO_CLIENT_ID\n') +
			'Cognito OAuth will not work. Set these in .env.local for development or configure in deployment.'
		);
	}

	return {
		loginWith: {
			oauth: {
				domain: domain || '',
				providers: ["Google"],
				redirectSignIn: [redirectSignIn],
				redirectSignOut: [redirectSignOut],
				responseType: "code" as const,
				scopes: ["openid", "email", "profile", "aws.cognito.signin.user.admin"],
			},
		},
		userPoolId: userPoolId || '',
		userPoolClientId: clientId || '',
		region,
	} as CognitoUserPoolConfig;
};

export const amplifyConfig = {
	Auth: {
		Cognito: getCognitoConfig(),
	} as AuthConfig
};
