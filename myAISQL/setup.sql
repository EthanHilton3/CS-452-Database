-- Chick-fil-A restaurant database (SQLite)

create table address (
    address_id integer primary key,
    street varchar(100) not null,
    city varchar(50) not null,
    state char(2) not null,
    zip_code varchar(10) not null,
    country varchar(50) not null default 'USA'
);

create table person (
    person_id integer primary key,
    first_name varchar(50) not null,
    last_name varchar(50) not null,
    email varchar(100) unique,
    phone_number varchar(15),
    address_id integer,
    foreign key (address_id) references address (address_id)
);

-- companies that supply ingredients to locations
create table supplier (
    supplier_id integer primary key,
    name varchar(100) not null,
    phone_number varchar(15),
    email varchar(100),
    address_id integer,
    foreign key (address_id) references address (address_id)
);

-- manager_id is nullable because location and employee reference each other
create table location (
    location_id integer primary key,
    name varchar(100) not null,
    address_id integer not null,
    phone_number varchar(15),
    manager_id integer,
    owner_id integer,
    foreign key (address_id) references address (address_id),
    foreign key (manager_id) references employee (person_id),
    foreign key (owner_id) references person (person_id)
);

-- opening hours per day of the week (0 = Sunday ... 6 = Saturday)
-- no row for a day means the location is closed that day
create table location_hours (
    location_id integer not null,
    day_of_week integer not null check (day_of_week between 0 and 6),
    open_time time not null,
    close_time time not null,
    primary key (location_id, day_of_week),
    foreign key (location_id) references location (location_id)
);

create table employee (
    person_id integer primary key,
    location_id integer not null,
    hourly_wage decimal(5,2) not null,
    start_date date not null,
    manager_id integer,
    foreign key (person_id) references person (person_id),
    foreign key (location_id) references location (location_id),
    foreign key (manager_id) references employee (person_id)
);

-- each hourly shift an employee works
create table shift (
    shift_id integer primary key,
    employee_id integer not null,
    location_id integer not null,
    start_time datetime not null,
    end_time datetime not null,
    foreign key (employee_id) references employee (person_id),
    foreign key (location_id) references location (location_id)
);

create table customer (
    person_id integer primary key,
    loyalty_points integer not null default 0,
    loyalty_status varchar(10) not null default 'Member'
        check (loyalty_status in ('Member', 'Silver', 'Red', 'Signature')),
    fav_location_id integer,
    foreign key (person_id) references person (person_id),
    foreign key (fav_location_id) references location (location_id)
);

-- price is the current menu price; order_item stores the price actually charged
create table menu_item (
    menu_item_id integer primary key,
    name varchar(100) not null unique,
    price decimal(6,2) not null,
    calories integer
);

-- e.g. milk, wheat, soy, egg, peanut, tree nut
create table allergen (
    allergen_id integer primary key,
    name varchar(50) not null unique
);

create table ingredient (
    ingredient_id integer primary key,
    name varchar(100) not null unique
);

-- which allergens each ingredient contains
create table ingredient_allergen (
    ingredient_id integer not null,
    allergen_id integer not null,
    primary key (ingredient_id, allergen_id),
    foreign key (ingredient_id) references ingredient (ingredient_id),
    foreign key (allergen_id) references allergen (allergen_id)
);

-- which ingredients go into each menu item (a menu item's allergens come through its ingredients)
create table menu_item_ingredient (
    menu_item_id integer not null,
    ingredient_id integer not null,
    primary key (menu_item_id, ingredient_id),
    foreign key (menu_item_id) references menu_item (menu_item_id),
    foreign key (ingredient_id) references ingredient (ingredient_id)
);

-- stock of each ingredient at each location, and who supplies it
create table inventory (
    location_id integer not null,
    ingredient_id integer not null,
    supplier_id integer,
    quantity_on_hand decimal(10,2) not null default 0,
    unit varchar(15) not null,
    primary key (location_id, ingredient_id),
    foreign key (location_id) references location (location_id),
    foreign key (ingredient_id) references ingredient (ingredient_id),
    foreign key (supplier_id) references supplier (supplier_id)
);

-- customer_id is null for guest orders (drive-thru or counter, no loyalty account)
create table customer_order (
    order_id integer primary key,
    customer_id integer,
    location_id integer not null,
    order_time datetime not null,
    order_type varchar(15) not null
        check (order_type in ('drive-thru', 'dine-in', 'mobile-pickup', 'delivery')),
    status varchar(10) not null default 'placed'
        check (status in ('placed', 'preparing', 'ready')),
    payment_method varchar(10) not null
        check (payment_method in ('cash', 'credit', 'debit', 'gift_card', 'app')),
    sales_tax decimal(6,2) not null,
    total_cost decimal(8,2) not null,
    foreign key (customer_id) references customer (person_id),
    foreign key (location_id) references location (location_id)
);

-- menu items in an order; price_charged is the unit price at the time of the order
create table order_item (
    order_id integer not null,
    menu_item_id integer not null,
    quantity integer not null default 1 check (quantity > 0),
    price_charged decimal(6,2) not null,
    primary key (order_id, menu_item_id),
    foreign key (order_id) references customer_order (order_id),
    foreign key (menu_item_id) references menu_item (menu_item_id)
);

-- a customer's saved favorite orders (replaces customer.fav_order_id, which made a circular reference)
create table customer_favorite_order (
    customer_id integer not null,
    order_id integer not null,
    primary key (customer_id, order_id),
    foreign key (customer_id) references customer (person_id),
    foreign key (order_id) references customer_order (order_id)
);
