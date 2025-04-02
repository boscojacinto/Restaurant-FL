const OpenAI = require('openai');

const model = new OpenAI({
	apiKey: 'dummy-key',
	baseURL: 'http://localhost:5000/v1'
});


async function main() {
	const stream = await model.chat.completions.create({
		model: 'bartowski/Dans-PersonalityEngine-v1.0.0-8b-GGUF',
		messages: [{role:'user', content: 'Tell me a short story?'}],
		stream: true,
	})

	for await (const chunk of stream) {
		const content = chunk.choices[0].delta.content || '';

		if (content) {
			process.stdout.write(content);
		}

		//process.stdout.write('\n');
	}
}

main();



