import { AuthConfig, CognitoUserPoolConfig } from '@aws-amplify/core';

// AWS Amplify configuration with placeholder Cognito values
export const amplifyConfig = {
	Auth: {
		Cognito: {
            loginWith: {
                oauth: {
                    domain: "us-east-1uhz7yreuq.auth.us-east-1.amazoncognito.com",
                    providers: ["Google"],
                    redirectSignIn: [(process.env.NEXT_PUBLIC_COGNITO_REDIRECT_SIGN_IN ?? "http://localhost:3000/")],
                    redirectSignOut: [(process.env.NEXT_PUBLIC_COGNITO_REDIRECT_SIGN_OUT ?? "http://localhost:3000/")],
                    responseType: "code" as const,
                    scopes: ["openid", "email", "profile", "aws.cognito.signin.user.admin"],
                },
            },
			userPoolId: 'us-east-1_uhz7yREuQ',
			userPoolClientId: '2vn45ed6rbe1c9cg58b2vgpt5u',
			region: 'us-east-1',
		} as CognitoUserPoolConfig
	} as AuthConfig
};
