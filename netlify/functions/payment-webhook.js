const { createClient } = require('@supabase/supabase-js');

// Initialize Supabase client
const supabaseUrl = 'https://tcwdbokruvlizkxcpkzj.supabase.co';
const supabaseKey = process.env.SUPABASE_SERVICE_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

exports.handler = async (event, context) => {
    // Only allow POST requests
    if (event.httpMethod !== 'POST') {
        return { statusCode: 405, body: 'Method Not Allowed' };
    }

    try {
        // Verify webhook signature
        const signature = event.headers['hyperswitch-signature'];
        if (!verifyWebhookSignature(event.body, signature, process.env.HYPERSWITCH_WEBHOOK_SECRET)) {
            return { statusCode: 401, body: 'Invalid signature' };
        }

        const payload = JSON.parse(event.body);
        const { type, data } = payload;

        switch (type) {
            case 'payment_intent.succeeded':
                // Payment was successful
                await handleSuccessfulPayment(data);
                break;

            case 'payment_intent.failed':
                // Payment failed
                await handleFailedPayment(data);
                break;

            case 'refund.succeeded':
                // Refund was processed
                await handleRefund(data);
                break;

            default:
                console.log('Unhandled webhook event:', type);
        }

        return {
            statusCode: 200,
            body: JSON.stringify({ received: true })
        };
    } catch (error) {
        console.error('Webhook error:', error);
        return {
            statusCode: 400,
            body: JSON.stringify({ error: error.message })
        };
    }
};

async function handleSuccessfulPayment(data) {
    const { payment_intent, metadata } = data;
    const { order_id } = metadata;

    // Start a Supabase transaction
    const { data: order, error: orderError } = await supabase
        .from('pending_orders')
        .update({ 
            status: 'paid',
            payment_intent_id: payment_intent.id,
            paid_at: new Date().toISOString()
        })
        .eq('id', order_id)
        .select()
        .single();

    if (orderError) {
        throw new Error(`Order update failed: ${orderError.message}`);
    }

    // Create transaction record
    const { error: txError } = await supabase
        .from('transactions')
        .insert({
            order_id: order_id,
            amount: order.total,
            payment_type: 'card',
            payment_method: 'hyperswitch',
            status: 'completed',
            external_transaction_id: payment_intent.id,
            created_at: new Date().toISOString()
        });

    if (txError) {
        throw new Error(`Transaction creation failed: ${txError.message}`);
    }

    // Create escrow record
    const releaseDate = new Date();
    releaseDate.setDate(releaseDate.getDate() + 7); // 7-day escrow

    const { error: escrowError } = await supabase
        .from('escrow')
        .insert({
            order_id: order_id,
            amount: order.total,
            commission: order.total * 0.10, // 10% commission
            seller_amount: order.total * 0.90,
            payment_type: 'card',
            release_date: releaseDate.toISOString(),
            status: 'pending'
        });

    if (escrowError) {
        throw new Error(`Escrow creation failed: ${escrowError.message}`);
    }
}

async function handleFailedPayment(data) {
    const { payment_intent, metadata } = data;
    const { order_id } = metadata;

    // Update order status
    const { error: orderError } = await supabase
        .from('pending_orders')
        .update({ 
            status: 'payment_failed',
            payment_intent_id: payment_intent.id,
            error_message: data.error?.message
        })
        .eq('id', order_id);

    if (orderError) {
        throw new Error(`Failed to update order status: ${orderError.message}`);
    }
}

async function handleRefund(data) {
    const { refund, payment_intent } = data;

    // Find the original transaction
    const { data: transaction, error: txError } = await supabase
        .from('transactions')
        .select('*')
        .eq('external_transaction_id', payment_intent.id)
        .single();

    if (txError) {
        throw new Error(`Transaction lookup failed: ${txError.message}`);
    }

    // Record the refund
    const { error: refundError } = await supabase
        .from('refunds')
        .insert({
            transaction_id: transaction.id,
            amount: refund.amount / 100, // Convert from cents
            refund_id: refund.id,
            status: 'completed',
            created_at: new Date().toISOString()
        });

    if (refundError) {
        throw new Error(`Refund recording failed: ${refundError.message}`);
    }
}

function verifyWebhookSignature(payload, signature, secret) {
    // TODO: Implement proper signature verification
    // This will depend on Hyperswitch's signature format
    // Example implementation:
    const crypto = require('crypto');
    const hmac = crypto.createHmac('sha256', secret);
    const expectedSignature = hmac.update(payload).digest('hex');
    return crypto.timingSafeEqual(
        Buffer.from(signature),
        Buffer.from(expectedSignature)
    );
}