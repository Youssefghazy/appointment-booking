This is a system for scheduling appointments.An appointment booking system.

## What is this?
A basic site which allows individuals to sign up for an appointment for 1 service.
There is just one calendar (suppose one person provides the service,
As one tutor or one hairdresser (). There's no need to have an account — to use the app.The app can be used without an account.
They directly book them.

## Who uses it
The customers are those who come to the page and wish to make a booking.
The service owner (admin): the person who provides the service, who
  needs to look at what's scheduled.

## Main goal
Allow a customer to select an open time slot and reserve it without an account,
and ensure that no two people get the same slot.

## User stories
1 As a customer, I want to know when the times are available so that I can:
   Choose One that fits Me.
2 When I am a customer, I want to make a booking for an open slot, giving the name of the customer to book.
   Contact information, so the owner is aware of who is arriving.
3 As a customer, I want to receive a confirmation that my booking has been accepted.
4 I want to see all bookings I have coming up in one place as the owner.
   I know my schedule.
5 I should not be able as a customer to book a slot which has already been taken by another customer.
   already took.
6 I do not want to schedule an appointment that has already been made by another person, and I don't want it to be old.
   Cleaning up the list that is to follow.

The basic booking flow is as follows:
1 The first step is the customer opens the booking page.
2 Customer reads the available "time slots" for the next few days.
3 Customer selects one of the opened slots.
4 Customer enters their name, email and phone number.
5 Customer confirms the booking.
6 Then that slot is taken, and it's not available to anyone else.
7 Customer receives a Booking confirmed message.

## Rules / requirements
- A slot can only ever be booked once. No double-booking — even if two
  People attempt to reserve the same time period at nearly the same time.
No account or log-in is required.
The owner can view a list of all bookings, along with the customer's
  Name and contact details.
- There is only one fixed length of appointment, as all of them are the same length.
  service.
- The business has restricted hours/days that it is open. Slots
  The hours outside of these should never be reserved.
- If a slot is booked then other customers should consider it booked.
  right away.

## What the owner can do
View All Future Bookings:
- Cancel a booking (unless there is a customer calling to cancel it).

Out of scope (not building this time)
- Several services or several staff calendars.
- Payments or deposits.
- Automatic email/SMS reminders.
- Customer accounts, login, or booking history.
- A mobile app—this can be done with a website.

## Example scenario
Youssef goes to the booking page on Monday and notices that there are some spaces available for the
rest of the week. She selects Wednesday at 2:00 PM, writes her name and
This is the telephone number and confirms. After a minute, Tom clicks the same page —
His Wednesday time is now booked at 2:00 PM.