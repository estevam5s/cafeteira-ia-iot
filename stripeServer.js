const express = require('express');
const stripe = require('stripe')('sua_chave_secreta_stripe');

const app = express();
app.use(express.json());

app.post('/create-checkout-session', async (req, res) => {
    try {
        const { priceId } = req.body;

        const session = await stripe.checkout.sessions.create({
            payment_method_types: ['card'],
            line_items: [
                {
                    price: priceId,
                    quantity: 1,
                },
            ],
            mode: 'subscription',
            success_url: 'https://seusite.com/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url: 'https://seusite.com/pricing',
            automatic_tax: { enabled: true },
        });

        res.json({ id: session.id });
    } catch (error) {
        console.error('Erro:', error);
        res.status(500).json({ error: 'Erro ao criar sessão de checkout' });
    }
});

app.listen(3000, () => console.log('Servidor rodando na porta 3000'));